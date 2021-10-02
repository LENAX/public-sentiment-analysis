import logging
import re
import traceback
from datetime import datetime, timedelta
from logging import Logger
from multiprocessing import cpu_count
from typing import Callable, Dict, List, Optional, Tuple, Union

import pytz
from ai_services.mock_article_service.app.models.response_models import (
    ArticleCategory, ArticlePopularity, ArticleSummary)
from dateutil import parser as dt_parser
from spider_services.baidu_news_spider.app.rpc import (
    ArticleClassificationService, ArticlePopularityService,
    ArticleSummaryService)
from spider_services.common.models.data_models.parser_models import ParseResult

from ...common.core import (BaseRequestClient, BaseSpider, ParserContext,
                            ParserContextFactory)
from ...common.models.data_models import News
from ...common.models.db_models import NewsDBModel
from ...common.models.request_models import ParseRule, ScrapeRules, TimeRange
from ...common.service.base_services import BaseSpiderService
from ...common.utils import throttled

utc = pytz.UTC

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(funcName)s | %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S")
spider_service_logger = logging.getLogger(__name__)
spider_service_logger.setLevel(logging.DEBUG)


class BaiduNewsSpiderService(BaseSpiderService):
    """ A spider for crawling baidu news
    
    You can crawl search engine pages with this service if the result page has a paging parameter.
    Provide the paging parameter and the link result url pattern to crawl raw results.
    If extraction rules are provided, this service will try to extract information from raw results.
    
    """

    def __init__(self,
                 request_client: BaseRequestClient,
                 spider_class: BaseSpider,
                 parse_strategy_factory: ParserContextFactory,
                 data_model: News,
                 db_model: NewsDBModel,
                 article_classification_service: ArticleClassificationService,
                 article_popularity_service: ArticlePopularityService,
                 article_summary_service: ArticleSummaryService,
                 datetime_parser: Callable = dt_parser,
                 throttled_fetch: Callable = throttled,
                 logger: Logger = spider_service_logger,
                 **kwargs) -> None:
        self._request_client = request_client
        self._spider_class = spider_class
        self._parse_strategy_factory = parse_strategy_factory
        self._data_model = data_model
        self._db_model = db_model
        self._article_classification_service = article_classification_service
        self._article_popularity_service = article_popularity_service
        self._article_summary_service = article_summary_service
        self._datetime_parser = datetime_parser
        self._throttled_fetch = throttled_fetch
        self._logger = logger
        self._create_time_string_extractors()

    def _create_time_string_extractors(self):
        self._cn_time_string_extractors = {
            re.compile('\d{1,2}秒前'):
                lambda now, time_str: now -
                timedelta(seconds=int(re.search('\d+', time_str).group(0))),
            re.compile('\d{1,2}分钟前'):
                lambda now, time_str: now -
                timedelta(minutes=int(re.search('\d+', time_str).group(0))),
            re.compile('\d{1,2}小时前'):
                lambda now, time_str: now -
                timedelta(hours=int(re.search('\d+', time_str).group(0))),
            re.compile('\d{1,2}天前'):
                lambda now, time_str: now -
                timedelta(days=int(re.search('\d+', time_str).group(0))),
            re.compile('昨天\d{1,2}:\d{1,2}'):
                lambda now, time_str: (now - timedelta(days=1)).replace(
                    hour=int(re.findall('\d+', time_str)[0]),
                    minute=int(re.findall('\d+', time_str)[1])),
            re.compile('\d{1,2}月\d{1,2}日'):
                lambda now, time_str: datetime(
                    now.year,
                    int(re.findall('\d+', time_str)[0]),
                int(re.findall('\d+', time_str)[1])),
            re.compile('\d{1,2}年\d{1,2}月\d{1,2}日'):
                lambda now, time_str: datetime(*(re.findall('\d+', time_str)))
        }

    def _standardize_datetime(self, time_str):
        """ Convert non standard format time string to standard datetime format
        
        Non standard cn time strings:
        1. 58分钟前
        2. 1小时前
        3. 昨天13:15
        4. 6月5日
        5. 5天前
        
        """
        today = datetime.now()
        converted = datetime(today.year, today.month, today.day)

        if len(time_str) == 0:
            return converted

        for pattern in self._cn_time_string_extractors:
            if pattern.match(time_str):
                converted = self._cn_time_string_extractors[pattern](
                    today, time_str)
                return converted

        return converted
    
    def _build_news_query_urls(self, base_url: str, keywords: List[str], max_page: int, past_days: int = 30) -> List[str]:
        search_urls = [f"{base_url}&rtt=4&bsst=1&cl=2&wd={kw}&rn=50&pn={page_number}&lm=30"
                       for page_number in range(max_page)
                       for kw in keywords]
        self._logger.info(search_urls)
        return search_urls
    
    def _fill_news_contents_blocks(self, news_query_pages: List[Tuple[str, str]], parser: ParserContext, parse_rules: List[ParseRule]):
        parsed_search_result = []

        self._logger.info(f"Parsing news blocks..")

        for _, raw_page in news_query_pages:
            search_results = parser.parse(raw_page, parse_rules)

            # standardize datetime
            for result in search_results:
                result_attributes = result.value
                if 'publishDate' in result_attributes:
                    result_attributes['publishDate'].value = self._standardize_datetime(
                        result_attributes['publishDate'].value)

            parsed_search_result.extend(search_results)

        self._logger.info(f"News list is parsed.")
        self._logger.info(f"News' publish dates standardized.")
        
        return parsed_search_result
    
    def _apply_date_range_filter(self, parsed_search_result: Union[List[ParseResult], List[News]], time_range: TimeRange):
        def _within_date_range(result: Union[ParseResult, News], past_days: Optional[int], start_date: Optional[datetime], end_date: Optional[datetime]):
            publish_date = result.value['publishDate'].value if type(result) is ParseResult else result.publishDate
            
            if publish_date is None:
                return False
            
            if past_days:
                try:
                    return publish_date >= datetime.now() - timedelta(days=past_days)
                except TypeError:
                    return publish_date >= utc.localize(datetime.now() - timedelta(days=past_days))
                    
            elif start_date is not None and end_date is not None:
                return end_date <= publish_date < start_date
            elif start_date is not None:
                return publish_date >= start_date
            elif end_date is not None:
                return publish_date < end_date
            else:
                return False
        
        self._logger.info(f"Applying time filters")
        parsed_search_result = [result for result in parsed_search_result
                                if _within_date_range(result, time_range.past_days, time_range.start_date, time_range.end_date)]
        
        return parsed_search_result
    
    
    def _apply_keyword_filter(self,  parsed_search_result: List[ParseResult], keywords_to_exclude: List[str]):
        exclude_kws = "|".join(keywords_to_exclude)
        exclude_patterns = re.compile(f'^((?!{exclude_kws}).)*$')
        parsed_search_result = [result for result in parsed_search_result
                                if ('abstract' in result.value and
                                    'title' in result.value and
                                    re.finditer(exclude_patterns, result.value['abstract']) and
                                    re.finditer(exclude_patterns, result.value['title']))]
        return parsed_search_result
    
    
    async def _fetch_news(self, parsed_search_result: List[ParseResult], max_concurrency: int):
        if len(parsed_search_result) == 0:
            return []
        
        content_urls = [result.value['link'].value for result in parsed_search_result]
        content_spiders = self._spider_class.create_from_urls(
            content_urls, self._request_client)
        content_pages = await self._throttled_fetch(max_concurrency, [spider.fetch() for spider in content_spiders])

        self._logger.info(f"Fetched {len(content_pages)} news pages")
        return content_pages
    
    def _to_news(self, parsed_results: List[ParseResult]) -> List[News]:
        try:
            news = [self._data_model.parse_obj(result.value_to_dict()) for result in parsed_results]
            return news
        except Exception as e:
            traceback.print_exc()
            self._logger.error(e)
            return []
    
    def _get_keyword_from_url(self, url: str):
        if type(url) is not str or len(url) == 0:
            return ""
        
        query_args = url.split("&")
        if len(query_args) < 2:
            return ""
        
        keyword_arg = [arg for arg in query_args if arg.startswith('wd=') or arg.startswith('word=')]
        if len(keyword_arg) == 0:
            return ""
        
        return keyword_arg[5:]
    
    async def _fill_news_contents(self, news_dict: Dict[str, News], content_pages: List[Tuple[str, str]],
                                  content_parser: ParserContext,  parse_rules: List[ParseRule], theme_id: int) -> None:        
        try:
            self._logger.info(f"Start parsing news pages")

            for i, page in enumerate(content_pages):
                self._logger.info(f"parsing {i+1}/{len(content_pages)}")
                content_url, content_page = page
                if len(content_page) == 0:
                    self._logger.error(f"failed to fetch news from url: {content_url}")
                    news_dict.pop(content_url, None)
                    continue

                parsed_contents = content_parser.parse(content_page, parse_rules)
                self._logger.info(f"parsing completed.")
                
                if all([len(data.value) == 0 for data in parsed_contents]):
                    self._logger.error(f"failed to parse content from url: {content_url}")
                    news_dict.pop(content_url, None)
                    continue
                
                content_dict = {
                    result.name: result.value for result in parsed_contents}
                news: News = news_dict[content_url]
                news.date = content_dict['publish_time'] if 'publish_time' in content_dict else news.publishDate.strftime("%Y-%m-%d")
                
                try:
                    news.publishDate = self._datetime_parser.parse(content_dict['publish_time']) if 'publish_time' in content_dict and len(content_dict['publish_time']) > 0 else news.publishDate
                except Exception as e:
                    self._logger.error(f"Parse datetime failed.. Error: {e}")
                    self._logger.info("Try to standardize datetime in Chinese...")
                    news.publishDate = self._standardize_datetime(content_dict['publish_time'])
                    
                try:
                    news.content = content_dict['content'] if 'content' in content_dict else ''
                    
                    keyword = self._get_keyword_from_url(content_url)
                    
                    summary, popularity, article_category = await self._throttled_fetch(3, [
                        self._article_summary_service.get_summary(theme_id, keyword, news.title, news.content),
                        self._article_popularity_service.get_popularity(theme_id, keyword, news.title, news.content),
                        self._article_classification_service.is_medical_article(theme_id, keyword, news.title, news.content)
                    ])
                    
                    self._logger.info(f'Summary: {summary}')
                    self._logger.info(f'popularity: {popularity}')
                    self._logger.info(f'is medical article: {article_category}')
                    
                    news.summary = summary.abstract_result
                    news.popularity = popularity.hot_value
                    news.is_medical_article = article_category.whether_medical_result
                except Exception as e:
                    traceback.print_exc()
                    self._logger.error(e)
                    
        except Exception as e:
            traceback.print_exc()
            self._logger.error(e)
            raise e
        
    def _apply_news_category_filter(self, news_dict: Dict[str, News]):
        for key, news in news_dict.items():
            if not news.is_medical_article:
                news_dict.pop(key, None)
                
        return news_dict
    
    def _apply_keywords_filter(self, news_dict: Dict[str, News], keywords: List[str]):
        for key in list(news_dict.keys()):
            keyword_included = False
            for keyword in keywords:
                if keyword in news_dict[key].content:
                    keyword_included = True
                    break
            if len(keywords) > 0 and not keyword_included:
                news_dict.pop(key)

        return news_dict
        
    async def crawl(self, urls: List[str], rules: ScrapeRules) -> None:
        """ Crawl search results within given rules like time range, keywords, and etc.
        
        User will provide the search page url of Baidu News (https://www.baidu.com/s?tn=news&ie=utf-8).
        This spider will automatically generate the actual search urls.

        Args:
            urls: baidu news url
            rules: rules the spider should follow. This mode expects keywords and size from users.
        """
        # if user provides no url, use default url
        try:
            # require the user to provide url, max_pages and keywords
            assert (len(urls) > 0 and
                    type(rules.max_pages) is int and rules.max_pages > 0 and
                    rules.keywords is not None and
                    len(rules.keywords.include) > 0 and rules.parsing_pipeline is not None and 
                    len(rules.parsing_pipeline) >= 2 and type(rules.theme_id) is int)

            self._logger.info("Parameters are validated. Prepare crawling...")
            self._logger.info("Start crawling news...")

            # generate search page urls given keywords and page limit
            news_query_urls = self._build_news_query_urls(
                urls[0], rules.keywords.include, rules.max_pages, rules.time_range.past_days)
            spiders = self._spider_class.create_from_urls(news_query_urls, self._request_client)

            # concurrently fetch search results with a concurrency limit
            # TODO: could boost parallelism by running parsers at the same time
            search_result_pages = await self._throttled_fetch(
                rules.max_concurrency, [spider.fetch() for spider in spiders])

            self._logger.info(
                f"Crawl completed. Fetched {len(search_result_pages)} results.")
            self._logger.info(f"Start crawling news pages...")
            self._logger.info(f"Parsing news list...")
            # for now, the pipeline is fixed to the following
            # 1. extract all search result blocks from search result pages (title, href, abstract, date)
            # step 1 will produce a list of List[ParseResult], and have to assume the order to work correctly
            # collect search results from parser, which has the form ParseResult(name=item, value={'attribute': ParseResult(name='attribute', value='...')})
            search_page_parser = self._parse_strategy_factory.create(rules.parsing_pipeline[0].parser)
            parsed_search_result = self._fill_news_contents_blocks(search_result_pages, search_page_parser, rules.parsing_pipeline[0].parse_rules)

            # 2. if date is provided, parse date strings and include those pages within date range
            if (len(parsed_search_result) > 0 and rules.time_range):
                self._logger.info(f"Applying time filters")
                parsed_search_result = self._apply_date_range_filter(parsed_search_result, rules.time_range)

            # 3. if keyword exclude is provided, exclude all pages having those keywords
            if (len(parsed_search_result) > 0 and rules.keywords and rules.keywords.exclude):
                self._logger.info(f"Applying keyword filters...")
                parsed_search_result = self._apply_keywords_filter(parsed_search_result, rules.keywords.exclude)

            news_list = self._to_news(parsed_search_result)
            news_dict = {news.link: news for news in news_list}

            self._logger.info(f"Got {len(parsed_search_result)} after filtering...")
            self._logger.info(f"Start crawling news pages...")
           
            # 4. fetch remaining pages
            content_pages = await self._fetch_news(parsed_search_result, rules.max_concurrency)

            # 5. use the last pipeline and extract contents. (title, content, url)
            self._logger.info(f"Start parsing news pages")
            content_parser = self._parse_strategy_factory.create(
                rules.parsing_pipeline[1].parser)
            await self._fill_news_contents(news_dict, content_pages, content_parser, 
                                           rules.parsing_pipeline[1].parse_rules, rules.theme_id)
            
            if len(rules.keywords.must_include) > 0:
                news_dict = self._apply_keywords_filter(news_dict, rules.keywords.must_include)
                
            news_dict = self._apply_news_category_filter(news_dict)
            
            filtered_news = news_dict.values()
            if (len(parsed_search_result) > 0 and rules.time_range):
                self._logger.info(f"Applying time filters again using articles' publish time.")
                filtered_news = self._apply_date_range_filter(
                    news_dict.values(), rules.time_range)
            
            results = []
            for news in filtered_news:
                news_db_object = self._db_model.parse_obj(news)
                news_db_object.themeId = rules.theme_id
                results.append(news_db_object)

            # 6. finally save results to db
            if len(results) > 0:
                self._logger.info(f"Saving results...")
                await self._db_model.insert_many(results)
                self._logger.info("Done!")
            else:
                self._logger.info("No new results retrieved in this run...")

        except Exception as e:
            traceback.print_exc()
            self._logger.error(e)
            raise e
            





if __name__ == "__main__":
    import asyncio
    from os import getcwd
    from typing import Any

    from devtools import debug
    from motor.motor_asyncio import AsyncIOMotorClient
    from yaml import CDumper as Dumper
    from yaml import CLoader as Loader
    from yaml import dump, load

    from ...common.core import CrawlerContextFactory, RequestClient, Spider
    from ...common.models.data_models import RequestHeader
    from ...common.models.request_models import (KeywordRules, ParseRule,
                                                 ParsingPipeline, ScrapeRules,
                                                 TimeRange)


    def create_client(host: str, username: str,
                      password: str, port: int,
                      db_name: str) -> AsyncIOMotorClient:
        return AsyncIOMotorClient(
            f"mongodb://{username}:{password}@{host}:{port}/{db_name}?authSource=admin")


    def load_service_config(
        config_name: str,
        loader_func: Callable=load,
        loader_class: Any=Loader,
        config_class: Any = ScrapeRules,
        config_path: str = f"{getcwd()}/spider_services/service_configs"
    ) -> object:
        with open(f"{config_path}/{config_name}.yml", "r") as f:
            config_text = f.read()
            parsed_obj = loader_func(config_text, Loader=loader_class)
            config_obj = config_class.parse_obj(parsed_obj)
            return config_obj

    def save_config(config, path, dump: Any = dump, dump_class: Any = Dumper):
        with open(path, 'w+') as f:
            config_text = dump(config, Dumper=dump_class)
            f.write(config_text)
            
    def make_cookies(cookie_text):
        cookie_strings = cookie_text.replace("\n", "").replace(" ", "").split(";")
        cookies = {}
        for cookie_str in cookie_strings:
            try:
                key, value = cookie_str.split("=")
                cookies[key] = value
            except IndexError:
                print(cookie_str)
            except ValueError:
                print(cookie_str)
        return cookies

    async def test_spider_services(db_client,
                                   db_name,
                                   headers,
                                   cookies,
                                   client_session_class,
                                   spider_class,
                                   parse_strategy_factory,
                                   crawling_strategy_factory,
                                   spider_service_class,
                                   data_model,
                                   result_model_class,
                                   test_urls,
                                   rules):
        db = db_client[db_name]
        result_model_class.db = db

        async with (await client_session_class(headers=headers, cookies=cookies)) as client_session:
            article_classification_service = ArticleClassificationService(
                'http://localhost:9000/article-category', client_session, ArticleCategory)
            article_popularity_service = ArticlePopularityService(
                'http://localhost:9000/article-popularity', client_session, ArticlePopularity
            )
            article_summary_service = ArticleSummaryService(
                'http://localhost:9000/content-abstract', client_session, ArticleSummary
            )

            spider_service = spider_service_class(request_client=client_session,
                                                  spider_class=spider_class,
                                                  parse_strategy_factory=parse_strategy_factory,
                                                  crawling_strategy_factory=crawling_strategy_factory,
                                                  data_model=data_model,
                                                  db_model=result_model_class,
                                                  article_classification_service=article_classification_service,
                                                  article_popularity_service=article_popularity_service,
                                                  article_summary_service=article_summary_service)
            await spider_service.crawl(test_urls, rules)

    cookie_text = """
    BIDUPSID=C2730507E1C86942858719FD87A61E58; PSTM=1591763607; BDUSS=1jdUJiZUIxc01RfkFTTUtoTXZaSFl1SDlPdEgzeGJGVEhkTDZzZ2ZIZlJSM1ZmSVFBQUFBJCQAAAAAAAAAAAEAAACILlzpAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAANG6TV~Ruk1fek; __yjs_duid=1_9e0d11606e81d46981d7148cc71a1d391618989521258; BCLID_BFESS=7682355843953324419; BDSFRCVID_BFESS=D74OJeC6263c72vemTUDrgjXg2-lavcTH6f3bGYZSp4POsT0C6gqEG0PEf8g0KubxY84ogKK3gOTH4PF_2uxOjjg8UtVJeC6EG0Ptf8g0f5; H_BDCLCKID_SF_BFESS=tbu8_IIMtCI3enb6MJ0_-P4DePop3MRZ5mAqoDLbKK0KfR5z3hoMK4-qWMtHe47KbD7naIQDtbonofcbK5OmXnt7D--qKbo43bRTKRLy5KJvfJo9WjAMhP-UyNbMWh37JNRlMKoaMp78jR093JO4y4Ldj4oxJpOJ5JbMonLafD8KbD-wD5LBeP-O5UrjetJyaR3R_KbvWJ5TMC_CDP-bDRK8hJOP0njM2HbMoj6sK4QjShPCb6bDQpFl0p0JQUReQnRm_J3h3l02Vh5Ie-t2ynLV2buOtPRMW20e0h7mWIbmsxA45J7cM4IseboJLfT-0bc4KKJxbnLWeIJIjj6jK4JKDG8ft5OP; BDUSS_BFESS=1jdUJiZUIxc01RfkFTTUtoTXZaSFl1SDlPdEgzeGJGVEhkTDZzZ2ZIZlJSM1ZmSVFBQUFBJCQAAAAAAAAAAAEAAACILlzpAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAANG6TV~Ruk1fek; H_WISE_SIDS=110085_127969_128698_164869_170704_171235_173017_173293_174035_174449_174661_174665_175038_175407_175609_175665_175756_176157_176348_176398_176418_176589_176678_176766_176960_176995_177085_177094_177168_177283_177317_177393_177401_177412_177520_177522_177565_177632_177727_177735_177787_178076_178152_178205_178327_178384_178639; BAIDUID=F77119553DDCA3E3D26F14FA5EBF834C:FG=1; BAIDUID_BFESS=F77119553DDCA3E3D26F14FA5EBF834C:FG=1; delPer=0; PSINO=7; BAIDU_WISE_UID=wapp_1632905041500_81;  BDORZ=B490B5EBF6F3CD402E515D22BCDA1598; BA_HECTOR=208500852hak2l047b1gldcon0q; H_PS_PSSID=; MBDFEEDSG=df5a2f94d6addda8f42862cac42480f2_1633073378; ab_sr=1.0.1_NDQ3Yjc4OTliYTExNWM4YmVjZDY4YTQzZmIyZWJhM2VjZDg2MmU2OGVlMzMxZTUyMmU0ZDE1NGZiMjI0OWU2OWI5NGQwZGQ5ODIzMTZjOTA1MzI5NjdhZTM5NDNmMjIwZjhjZWRlNDQyYjVjNTUyZDc5MWI2MGU5MGM2OTAyNjcyMDRkMTQ1ODRlOTFmNjZiMTE5NDIyN2JjYWYzZDFkMw==
    """
    cookies = make_cookies(cookie_text)

    headers = RequestHeader(
        accept="text/html, application/xhtml+xml, application/xml, image/webp, */*",
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",)
    use_db = 'test'
    db_client = create_client(host='localhost',
                              username='admin',
                              password='root',
                              port=27017,
                              db_name=use_db)
    urls = [
        "http://www.baidu.com/s?tn=news&ie=utf-8"
    ]
    print(urls)
    config = load_service_config("baidu_news")
    debug(config)
    
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test_spider_services(
        db_client=db_client,
        db_name=use_db,
        headers=headers.dict(),
        cookies=cookies,
        client_session_class=RequestClient,
        spider_class=Spider,
        parse_strategy_factory=ParserContextFactory,
        crawling_strategy_factory=CrawlerContextFactory,
        spider_service_class=BaiduNewsSpiderService,
        data_model=News,
        result_model_class=NewsDBModel,
        test_urls=urls,
        rules=config
    ))

