import re
import asyncio
from uuid import uuid5, NAMESPACE_OID
from functools import partial
from aiohttp import ClientSession
from datetime import datetime, timedelta
from typing import List, Any, Tuple, Callable, TypeVar
from motor.motor_asyncio import AsyncIOMotorDatabase
from concurrent.futures import ProcessPoolExecutor
from .base_services import BaseSpiderService, BaseServiceFactory
from ..models.data_models import (
    RequestHeader,
    URL,
    HTMLData,
)
from ..models.request_models import ScrapeRules
from ..models.db_models import Result
from ..enums import JobType
from ..utils import AsyncIterator
from ..core import BaseSpider, CrawlerContext, ParserContextFactory

""" Defines all spider services

Catalog
1. HTMLSpiderService
    - Scrape static web page and return its content

"""
SemaphoreClass = TypeVar("SemaphoreClass")
EventLoop = TypeVar("EventLoop")
ProcessPoolExecutorClass = TypeVar("ProcessPoolExecutorClass")


class HTMLSpiderService(BaseSpiderService):

    def __init__(self,
                 session: ClientSession,
                 spider_cls: BaseSpider,
                 parse_strategy_factory: ParserContextFactory,
                 result_db_model: Result,
                 html_data_model: HTMLData,
                 table_id_generator: Callable = partial(uuid5, NAMESPACE_OID),
                 semaphore_cls: SemaphoreClass = asyncio.Semaphore,
                 coroutine_runner: Callable = asyncio.gather
                 ) -> None:
        self._session = session
        self._spider_cls = spider_cls
        self._parse_strategy_factory= parse_strategy_factory
        self._result_db_model = result_db_model
        self._html_data_model = html_data_model
        self._table_id_generator = table_id_generator
        self._semaphore_class = semaphore_cls
        self._coroutine_runner = coroutine_runner


    async def _throttled_fetch(self, n, *tasks):
        semaphore = asyncio.Semaphore(n)

        async def sem_task(task):
            async with semaphore:
                return await task
        return await self._coroutine_runner(
            *(sem_task(task) for task in tasks), return_exceptions=True)

    async def crawl(self, urls: List[str], rules: ScrapeRules) -> None:
        """ Get html data given the data source

        Args: 
            data_src: List[str]
            rules: ScrapeRules
        """
        # try create many spiders
        spiders = self._spider_cls.create_from_urls(urls, self._session)

        html_pages = await self._throttled_fetch(
            rules.max_concurrency, *[spider.fetch() for spider in spiders])

        result_dt = datetime.now()
        html_data = [
            self._html_data_model(
                url=page[0], html=page[1], create_dt=result_dt)
            for page in html_pages
        ]
        result_name = f"result_{result_dt}"
        crawl_result = self._result_db_model(
            result_id=self._table_id_generator(result_name),
            name=result_name,
            description="",
            data=html_data,
            create_dt=result_dt
        )
        await crawl_result.save()


class SearchResultSpider(BaseSpiderService):
    """ A general spider for crawling search results. 
    
    You can crawl search engine pages with this service if the result page has a paging parameter.
    Provide the paging parameter and the link result url pattern to crawl raw results.
    If extraction rules are provided, this service will try to extract information from raw results.
    
    """

    def __init__(self,
                 session: ClientSession,
                 spider: BaseSpider,
                 parse_strategy_factory: ParserContextFactory,
                 result_db_model: Result,
                 html_data_model: HTMLData,
                 table_id_generator: Callable = partial(uuid5, NAMESPACE_OID),
                 semaphore_cls: SemaphoreClass = asyncio.Semaphore,
                 coroutine_runner: Callable = asyncio.gather
                ) -> None:
        self._session = session
        self._spider = spider
        self._result_db_model = result_db_model
        self._html_data_model = html_data_model
        self._table_id_generator = table_id_generator
        self._semaphore_class = semaphore_cls
        self._coroutine_runner = coroutine_runner

    async def crawl(self, urls: List[str], rules: ScrapeRules) -> None:
        """ Crawl search results """
        # TODO: implement this
        pass


class BaiduNewsSpider(BaseSpiderService):
    """ A spider for crawling baidu news
    
    You can crawl search engine pages with this service if the result page has a paging parameter.
    Provide the paging parameter and the link result url pattern to crawl raw results.
    If extraction rules are provided, this service will try to extract information from raw results.
    
    """

    def __init__(self,
                 session: ClientSession,
                 spider_cls: BaseSpider,
                 parse_strategy_factory: ParserContextFactory,
                 result_db_model: Result,
                 html_data_model: HTMLData,
                 table_id_generator: Callable = partial(uuid5, NAMESPACE_OID),
                 semaphore_cls: SemaphoreClass = asyncio.Semaphore,
                 coroutine_runner: Callable = asyncio.gather,
                 event_loop_getter: Callable = asyncio.get_event_loop,
                 process_pool_executor: ProcessPoolExecutorClass = ProcessPoolExecutor
                 ) -> None:
        self._session = session
        self._spider_cls = spider_cls
        self._parse_strategy_factory = parse_strategy_factory
        self._result_db_model = result_db_model
        self._html_data_model = html_data_model
        self._table_id_generator = table_id_generator
        self._semaphore_class = semaphore_cls
        self._coroutine_runner = coroutine_runner
        self._event_loop_getter = event_loop_getter
        self._process_pool_executor = process_pool_executor
        self._create_time_string_extractors()
        
    async def _throttled_fetch(self, max_concurrency: int, *tasks) -> Any:
        semaphore = asyncio.Semaphore(max_concurrency)

        async def sem_task(task):
            async with semaphore:
                return await task
        return await self._coroutine_runner(
                *(sem_task(task) for task in tasks), return_exceptions=True)

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
    
    def _group_fields_by(self, columns: List[str]):
        pass

    async def crawl(self, urls: List[str], 
                    rules: ScrapeRules,
                    paging_param: str = "pn") -> None:
        """ Crawl search results within given rules like time range, keywords, and etc.
        
        User will provide the search page url of Baidu News (https://www.baidu.com/s?tn=news&ie=utf-8).
        This spider will automatically generate the actual search urls.

        Args:
            urls: baidu news url
            rules: rules the spider should follow. This mode expects keywords and size from users.
        """
        # if user provides no url, use default url
        spiders = []

        # require the user to provide url, max_pages and keywords
        assert (len(urls) > 0 and 
                type(rules.max_pages) is int and 
                len(rules.keywords.include) > 0)

        # generate search page urls given keywords and page limit
        for search_base_url in urls:
            search_urls = [f"{search_base_url}&word={kw}&{paging_param}={page_number}"
                           for page_number in range(rules.max_pages)
                           for kw in rules.keywords.include]
            spiders.extend(self._spider_cls.create_from_urls(search_urls, self._session))

        # concurrently fetch search results with a concurrency limit
        # TODO: could boost parallelism by running parsers at the same time
        search_result_pages = await self._throttled_fetch(
            rules.max_concurrency, *[spider.fetch() for spider in spiders])

        # for now, the pipeline is fixed to the following
        # 1. extract all search result blocks from search result pages (title, href, abstract, date)
        # step 1 will produce a list of List[ParseResult], and have to assume the order to work correctly
        # collect search results from parser, which has the form ParseResult(name=item, value={'attribute': ParseResult(name='attribute', value='...')})
        parsed_search_result = []
        search_page_parser = self._parse_strategy_factory.create(
            rules.parsing_pipeline[0].parser)
        for _, raw_page in search_result_pages:
            search_results = search_page_parser.parse(
                raw_page, rules.parsing_pipeline[0].parse_rules)

            # standardize datetime
            for result in search_results:
                result_attributes = result.value
                if 'date' in result_attributes:
                    result_attributes['date'].value = self._standardize_datetime(
                        result_attributes['date'].value)

            parsed_search_result.extend(search_results)
        
        # 2. if date is provided, parse date strings and include those pages within date range
        if (len(parsed_search_result) > 0 and rules.time_range):
            if rules.time_range.past_days:
                last_date = datetime.now() - timedelta(days=rules.time_range.past_days)
                parsed_search_result = [result for result in parsed_search_result
                                        if 'date' in result.value and result.value['date'].value >= last_date]
            elif rules.time_range.date_before and rules.time_range.date_after:
                parsed_search_result = [result for result in parsed_search_result
                                        if ('date' in result.value and 
                                            rules.time_range.date_after <= result.value['date'].value < rules.time_range.date_before)]
            elif rules.time_range.date_before:
                parsed_search_result = [result for result in parsed_search_result
                                        if ('date' in result.value and
                                            rules.time_range.date_after <= result.value['date'].value)]
            elif rules.time_range.date_before and rules.time_range.date_after:
                parsed_search_result = [result for result in parsed_search_result
                                        if ('date' in result.value and
                                            result.value['date'].value < rules.time_range.date_before)]
                            
        # 3. if keyword exclude is provided, exclude all pages having those keywords
        if (len(parsed_search_result) > 0 and rules.keywords and rules.keywords.exclude):
            exclude_kws = "|".join(rules.keywords.exclude)
            exclude_patterns = re.compile(f'^((?!{exclude_kws}).)*$')
            parsed_search_result = [result for result in parsed_search_result
                                    if ('abstract' in result.value and 
                                        'title' in result.value and 
                                        re.finditer(exclude_patterns, result.value['abstract']) and
                                        re.finditer(exclude_patterns, result.value['title']))]
        
        # 4. fetch remaining pages
        if (len(parsed_search_result) > 0):
            content_urls = [result.value['href'].value for result in parsed_search_result]
            content_spiders = self._spider_cls.create_from_urls(content_urls, self._session)
            content_pages = await self._throttled_fetch(
                rules.max_concurrency, *[spider.fetch() for spider in content_spiders])
        
        # 5. use the last pipeline and extract contents. (title, content, url)
        content_parser = self._parse_strategy_factory.create(
            rules.parsing_pipeline[1].parser)
        parsed_content_results = []
        for content_url, content_page in content_pages:
            parsed_contents = {content.name: content
                               for content in content_parser.parse(
                               content_page, rules.parsing_pipeline[1].parse_rules)}
            parsed_contents['url'] = content_url
            parsed_content_results.append(parsed_contents)
            
        # 6. finally save results to db
        result_dt = datetime.now()
        results = [
            self._result_db_model(
                result_id=self._table_id_generator(result['title'].name),
                name=result['title'].value,
                description="",
                data=result.values(),
                create_dt=result_dt
            )
            for result in parsed_content_results
        ]
        await self._result_db_model.insert_many(results)





class WebCrawlingSpider(BaseSpiderService):

    def __init__(self, session: ClientSession, html_data_mapper: Any):
        pass


SPIDER_TYPES = {
    JobType.BASIC_PAGE_SCRAPING: HTMLSpiderService,
    JobType.SEARCH_RESULT_AGGREGATION: SearchResultSpider,
    JobType.WEB_CRAWLING: WebCrawlingSpider,
    JobType.BAIDU_NEWS_SCRAPING: BaiduNewsSpider
}

class SpiderFactory(BaseServiceFactory):

    def __init__(self):
        pass
    
    @staticmethod
    def create(spider_type: str, **kwargs):
        try:
            return SPIDER_TYPES[spider_type.lower()](**kwargs)
        except Exception:
            return None



if __name__ == "__main__":
    import asyncio
    from motor.motor_asyncio import AsyncIOMotorClient
    from ..models.request_models import (
        ScrapeRules, ParsingPipeline, ParseRule, KeywordRules, TimeRange
    )
    from ..core import Spider

    def create_client(host: str, username: str,
                      password: str, port: int,
                      db_name: str) -> AsyncIOMotorClient:
        return AsyncIOMotorClient(
            f"mongodb://{username}:{password}@{host}:{port}/{db_name}?authSource=admin")


    async def test_spider_services(db_client,
                                   db_name,
                                   headers,
                                   cookies,
                                   client_session_cls,
                                   spider_cls,
                                   parse_strategy_factory,
                                   spider_service_cls,
                                   result_model_cls,
                                   html_model_cls,
                                   test_urls,
                                   rules):
        db = db_client[db_name]
        result_model_cls.db = db
        html_model_cls.db = db

        async with client_session_cls(headers=headers, cookies=cookies) as client_session:
            # spider = spider_cls(request_client=client_session)
            spider_service = spider_service_cls(session=client_session,
                                                spider_cls=spider_cls,
                                                parse_strategy_factory=parse_strategy_factory,
                                                result_db_model=result_model_cls,
                                                html_data_model=html_model_cls)
            await spider_service.crawl(test_urls, rules)

    cookie_text = """BIDUPSID=C2730507E1C86942858719FD87A61E58;
    PSTM=1591763607; BAIDUID=0145D8794827C0813A767D21ADED26B4:FG=1;
    BDUSS=1jdUJiZUIxc01RfkFTTUtoTXZaSFl1SDlPdEgzeGJGVEhkTDZzZ2ZIZlJSM1ZmSVFBQUFBJCQAAAAAAAAAAAEAAACILlzpAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAANG6TV~Ruk1fek;
    __yjs_duid=1_9e0d11606e81d46981d7148cc71a1d391618989521258; BD_UPN=123253; BCLID_BFESS=7682355843953324419; BDSFRCVID_BFESS=D74OJeC6263c72vemTUDrgjXg2-lavcTH6f3bGYZSp4POsT0C6gqEG0PEf8g0KubxY84ogKK3gOTH4PF_2uxOjjg8UtVJeC6EG0Ptf8g0f5;
    H_BDCLCKID_SF_BFESS=tbu8_IIMtCI3enb6MJ0_-P4DePop3MRZ5mAqoDLbKK0KfR5z3hoMK4-qWMtHe47KbD7naIQDtbonofcbK5OmXnt7D--qKbo43bRTKRLy5KJvfJo9WjAMhP-UyNbMWh37JNRlMKoaMp78jR093JO4y4Ldj4oxJpOJ5JbMonLafD8KbD-wD5LBeP-O5UrjetJyaR3R_KbvWJ5TMC_CDP-bDRK8hJOP0njM2HbMoj6sK4QjShPCb6bDQpFl0p0JQUReQnRm_J3h3l02Vh5Ie-t2ynLV2buOtPRMW20e0h7mWIbmsxA45J7cM4IseboJLfT-0bc4KKJxbnLWeIJIjj6jK4JKDG8ft5OP;
    """
    cookie_strings = cookie_text.replace("\n","").replace(" ","").split(";")
    cookies = {}
    for cookie_str in cookie_strings:
        try:
            key, value = cookie_str.split("=")
            cookies[key] = value
        except IndexError:
            print(cookie_str)
        except ValueError:
            print(cookie_str)

    headers = RequestHeader(
        accept="text/html, application/xhtml+xml, application/xml, image/webp, */*",
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",
        cookie=str(cookies))
    use_db = 'spiderDB'
    db_client = create_client(host='localhost',
                              username='admin',
                              password='root',
                              port=27017,
                              db_name=use_db)
    urls = [f"http://www.baidu.com/s?rtt=1&bsst=1&cl=2&tn=news&ie=utf-8"]
    print(urls)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(test_spider_services(
        db_client=db_client,
        db_name=use_db,
        headers=headers.dict(),
        cookies=cookies,
        client_session_cls=ClientSession,
        spider_cls=Spider,
        parse_strategy_factory=ParserContextFactory,
        spider_service_cls=BaiduNewsSpider,
        result_model_cls=Result,
        html_model_cls=HTMLData,
        test_urls=urls,
        rules=ScrapeRules(
            max_concurrency=5,
            max_pages=1,
            keywords=KeywordRules(
                include=['空间站', '航天']),
            time_range=TimeRange(past_days=3),
            parsing_pipeline=[
                ParsingPipeline(
                    parser="list_item_parser",
                    parse_rules=[
                        ParseRule(
                            field_name='title',
                            rule_type='xpath',
                            rule="//h3/a"
                        ),
                        ParseRule(
                            field_name='href',
                            rule_type='xpath',
                            rule="//h3/a",
                            is_link=True
                        ),
                        ParseRule(
                            field_name='abstract',
                            rule_type='xpath',
                            rule="//span[contains(@class, 'c-font-normal') and contains(@class, 'c-color-text')]"
                        ),
                        ParseRule(
                            field_name='date',
                            rule_type='xpath',
                            rule="//span[contains(@class, 'c-color-gray2') and contains(@class, 'c-font-normal')]"
                        )
                    ]
                ),
                ParsingPipeline(
                    parser="general_news_parser",
                    parse_rules=[]
                )
            ],
        )
    ))

# (title, href, abstract, date)
