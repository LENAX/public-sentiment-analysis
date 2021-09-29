import logging
import re
from datetime import datetime, timedelta
from logging import Logger
from spider_services.common.models.data_models.parser_models import ParseResult
from typing import Callable, List, Tuple

from ...common.core import (BaseRequestClient, BaseSpider, ParserContext,
                            ParserContextFactory)
from ...common.models.data_models import News
from ...common.models.db_models import NewsDBModel
from ...common.models.request_models import ParseRule, ScrapeRules, TimeRange
from ...common.service.base_services import BaseSpiderService
from ...common.utils import throttled

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(funcName)s | %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S")
spider_service_logger = logging.getLogger(__name__)
spider_service_logger.setLevel(logging.DEBUG)


class BaiduNewsSpider(BaseSpiderService):
    """ A spider for crawling baidu news
    
    You can crawl search engine pages with this service if the result page has a paging parameter.
    Provide the paging parameter and the link result url pattern to crawl raw results.
    If extraction rules are provided, this service will try to extract information from raw results.
    
    """

    def __init__(self,
                 request_client: BaseRequestClient,
                 spider_class: BaseSpider,
                 parse_strategy_factory: ParserContextFactory,
                 db_model: NewsDBModel,
                 throttled_fetch: Callable = throttled,
                 logger: Logger = spider_service_logger,
                 **kwargs) -> None:
        self._request_client = request_client
        self._spider_class = spider_class
        self._parse_strategy_factory = parse_strategy_factory
        self._db_model = db_model
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
                lambda now, time_str: datetime(
                    now.year, now.month, now.day-1,
                    int(re.findall('\d+', time_str)[0]),
                    int(re.findall('\d+', time_str)[1])
            ),
            re.compile('\d{1,2}月\d{1,2}日'):
                lambda now, time_str: datetime(
                    now.year,
                    int(re.findall('\d+', time_str)[0]),
                int(re.findall('\d+', time_str)[1])),

            re.compile('\d{1,2}年\d{1,2}月\d{1,2}日'):
                lambda now, time_str: datetime(
                    *(re.findall('\d+', time_str))
            )
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
    
    def _build_news_query_urls(self, base_url: str, keywords: List[str], max_page: int) -> List[str]:
        search_urls = [f"{base_url}&word={kw}&pn={page_number}"
                       for page_number in range(max_page)
                       for kw in keywords]
        return search_urls
    
    def _parse_news_blocks(self, news_query_pages: List[Tuple[str, str]], parser: ParserContext, parse_rules: List[ParseRule]):
        parsed_search_result = []

        self._logger.info(f"Standardizing news' publish dates..")

        for _, raw_page in news_query_pages:
            search_results = parser.parse(raw_page, parse_rules)

            # standardize datetime
            for result in search_results:
                result_attributes = result.value
                if 'date' in result_attributes:
                    result_attributes['date'].value = self._standardize_datetime(
                        result_attributes['date'].value)

            parsed_search_result.extend(search_results)

        self._logger.info(f"News list is parsed.")
        self._logger.info(f"News' publish dates standardized.")
        
        return parsed_search_result
    
    def _apply_date_range_filter(self, parsed_search_result: List[ParseResult], time_range: TimeRange):
        self._logger.info(f"Applying time filters")
        if time_range.past_days:
            last_date = datetime.now() - timedelta(days=time_range.past_days)
            parsed_search_result = [result for result in parsed_search_result
                                    if 'date' in result.value and result.value['date'].value >= last_date]
        elif time_range.start_date and time_range.end_date:
            parsed_search_result = [result for result in parsed_search_result
                                    if ('date' in result.value and
                                        time_range.end_date <= result.value['date'].value < time_range.start_date)]
        elif time_range.start_date:
            parsed_search_result = [result for result in parsed_search_result
                                    if ('date' in result.value and
                                        time_range.end_date <= result.value['date'].value)]
        elif time_range.start_date and time_range.end_date:
            parsed_search_result = [result for result in parsed_search_result
                                    if ('date' in result.value and
                                        result.value['date'].value < time_range.start_date)]
        
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
        
        content_urls = [result.value['href'].value for result in parsed_search_result]
        content_spiders = self._spider_class.create_from_urls(
            content_urls, self._request_client)
        content_pages = await self._throttled_fetch(max_concurrency, [spider.fetch() for spider in content_spiders])

        self._logger.info(f"Fetched {len(content_pages)} news pages")
        return content_pages
    
    def _parse_news(self, content_pages: List[Tuple[str, str]], content_parser: ParserContext, parse_rules: List[ParseRule]) -> List[NewsDBModel]:
        self._logger.info(f"Start parsing news pages")
        results = []

        for i, page in enumerate(content_pages):
            self._logger.info(f"parsing {i}/{len(content_pages)}")
            content_url, content_page = page
            if len(content_page) == 0:
                self._logger.error(f"failed to fetch url: {content_url}")
                continue

            parsed_contents = content_parser.parse(content_page, parse_rules)
            content_dict = {result.name: result.value for result in parsed_contents}
            news = self._db_model.parse_obj(content_dict)
            news.link = content_url
            results.append(news)
            
        return results

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
                    type(rules.max_pages) is int and rules.keywords is not None and
                    len(rules.keywords.include) > 0 and rules.parsing_pipeline is not None and 
                    len(rules.parsing_pipeline) >= 2)

            self._logger.info("Parameters are validated. Prepare crawling...")
            self._logger.info("Start crawling news...")

            # generate search page urls given keywords and page limit
            news_query_urls = self._build_news_query_urls(
                urls[0], rules.keywords.include, rules.max_pages)
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
            parsed_search_result = self._parse_news_blocks(search_result_pages, search_page_parser, rules.parsing_pipeline[0].parse_rules)

            # 2. if date is provided, parse date strings and include those pages within date range
            if (len(parsed_search_result) > 0 and rules.time_range):
                self._logger.info(f"Applying time filters")
                parsed_search_result = self._apply_date_range_filter(parsed_search_result, rules.time_range)

            # 3. if keyword exclude is provided, exclude all pages having those keywords
            if (len(parsed_search_result) > 0 and rules.keywords and rules.keywords.exclude):
                self._logger.info(f"Applying keyword filters...")
                parsed_search_result = self._apply_keywords_filter(parsed_search_result, rules.keywords.exclude)

            self._logger.info(
                f"Got {len(parsed_search_result)} after filtering...")
            self._logger.info(f"Start crawling news pages...")
           
            # 4. fetch remaining pages
            content_pages = await self._fetch_news(parsed_search_result, rules.max_concurrency)

            # 5. use the last pipeline and extract contents. (title, content, url)
            self._logger.info(f"Start parsing news pages")
            content_parser = self._parse_strategy_factory.create(
                rules.parsing_pipeline[1].parser)
            results = self._parse_news(content_pages, content_parser, rules.parsing_pipeline[1].parse_rules)

            # 6. finally save results to db
            if len(results) > 0:
                self._logger.info(f"Saving results...")
                await self._db_model.insert_many(results)
                self._logger.info("Done!")
            else:
                self._logger.info("No new results retrieved in this run...")

        except Exception as e:
            print('An exception occurred')
