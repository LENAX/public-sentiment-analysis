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
                 result_db_model: Result,
                 html_data_model: HTMLData,
                 table_id_generator: Callable = partial(uuid5, NAMESPACE_OID),
                 semaphore_cls: SemaphoreClass = asyncio.Semaphore,
                 coroutine_runner: Callable = asyncio.gather
                 ) -> None:
        self._session = session
        self._spider_cls = spider_cls
        # self._parse_strategy_factory= parse_strategy_factory
        self._result_db_model = result_db_model
        self._html_data_model = html_data_model
        self._table_id_generator = table_id_generator
        self._semaphore_class = semaphore_cls
        self._coroutine_runner = coroutine_runner

    async def _throttled_fetch(self, url, params, semaphore) -> Tuple[str, str]:
        async with semaphore:
            return await self._spider.fetch(url, params)

    async def _throttled_spider_fetch(self, spider, semaphore) -> Tuple[str, str]:
        async with semaphore:
            return await spider.fetch()

    async def crawl(self, urls: List[str], rules: ScrapeRules) -> None:
        """ Get html data given the data source

        Args: 
            data_src: List[str]
            rules: ScrapeRules
        """
        semaphore = self._semaphore_class(rules.max_concurrency)
        # try create many spiders
        spiders = self._spider_cls.create_from_urls(urls, self._session)

        # html_pages = await self._coroutine_runner(
        #     *[self._throttled_fetch(url, rules.request_params, semaphore)
        #       for url in urls],
        #     return_exceptions=True)
        html_pages = await self._coroutine_runner(
            *[self._throttled_spider_fetch(spider, semaphore)
              for spider in spiders],
            return_exceptions=True)
        print(html_pages)
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
        

    async def _throttled_fetch(self, spider, semaphore) -> Tuple[str, str]:
        async with semaphore:
            return await spider.fetch()

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
            search_urls = [f"{search_base_url}&wd={kw}&{paging_param}={page_number}"
                           for page_number in range(rules.max_pages)
                           for kw in rules.keywords.include]
            spiders.extend(self._spider_cls.create_from_urls(search_urls, self._session))

        # concurrently fetch search results with a concurrency limit
        # TODO: could boost parallelism by running parsers at the same time
        semaphore = self._semaphore_class(rules.max_concurrency)
        search_result_pages = await self._coroutine_runner(
            *[self._throttled_fetch(spider, semaphore) for spider in spiders],
            return_exceptions=True)

        # for now, the pipeline is fixed to the following
        # 1. extract all search result blocks from search result pages (title, href, abstract, date)
        # step 1 will produce a list of List[ParseResult], and have to assume the order to work correctly
        parsed_search_result = []
        search_page_parser = self._parse_strategy_factory.create(
            rules.parsing_pipeline[0].parser)
        for raw_page in search_result_pages:
            parsed_page = {page.name: page 
                           for page in search_page_parser.parse(
                               raw_page, rules.parsing_pipeline[0].parse_rules)}
            # standardize datetime
            if 'date' in parsed_page:
                parsed_page['date'].value = self._standardize_datetime(
                    parsed_page['date'].value)

            parsed_search_result.append(parsed_page)
        
        # 2. if date is provided, parse date strings and include those pages within date range
        if (len(parsed_search_result) > 0 and rules.time_range):
            if rules.time_range.past_days:
                last_date = datetime.now() - timedelta(days=rules.time_range.past_days)
                parsed_search_result = [result for result in parsed_search_result
                                        if 'date' in result and result['date'].value >= last_date]
            elif rules.time_range.date_before and rules.time_range.date_after:
                parsed_search_result = [result for result in parsed_search_result
                                        if ('date' in result and 
                                            rules.time_range.date_after <= result['date'].value < rules.time_range.date_before)]
            elif rules.time_range.date_before:
                parsed_search_result = [result for result in parsed_search_result
                                        if ('date' in result and
                                            rules.time_range.date_after <= result['date'].value)]
            elif rules.time_range.date_before and rules.time_range.date_after:
                parsed_search_result = [result for result in parsed_search_result
                                        if ('date' in result and
                                            result['date'].value < rules.time_range.date_before)]
                            
        # 3. if keyword exclude is provided, exclude all pages having those keywords
        if (len(parsed_search_result) > 0 and rules.keywords and rules.keywords.exclude):
            exclude_kws = "|".join(rules.keywords.exclude)
            exclude_patterns = re.compile(f'^((?!{exclude_kws}).)*$')
            parsed_search_result = [result for result in parsed_search_result
                                    if ('abstract' in result and 
                                        'title' in result and 
                                        re.find_iter(exclude_patterns, result['abstract']) and
                                        re.find_iter(exclude_patterns, result['title']))]
        
        # 4. fetch remaining pages
        if (len(parsed_search_result) > 0):
            content_urls = [result['href'].value for result in parsed_search_result]
            content_spiders = self._spider_cls.create_from_urls(content_urls)
            content_pages = await self._coroutine_runner(
                *[self._throttled_fetch(spider, semaphore)
                  for spider in content_spiders],
                return_exceptions=True)
        
        # 5. use the last pipeline and extract contents. (title, content, url)
        content_parser = self._parse_strategy_factory.create(
            rules.parsing_pipeline[1].parser)
        parsed_content_results = []
        for content_page in content_pages:
            parsed_contents = {content.name: content
                               for content in content_parser.parse(
                               content_page, rules.parsing_pipeline[1].parse_rules)}
            parsed_content_results.append(parsed_contents)
            
        # 6. finally save results to db
        result_dt = datetime.now()
        results = [
            self._result_db_model(
                result_id=self._table_id_generator(result['title'].name),
                name=result['title'].name,
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
    from ..models.request_models import ScrapeRules
    from ..core import Spider

    def create_client(host: str, username: str,
                      password: str, port: int,
                      db_name: str) -> AsyncIOMotorClient:
        return AsyncIOMotorClient(
            f"mongodb://{username}:{password}@{host}:{port}/{db_name}?authSource=admin")


    async def test_spider_services(db_client,
                                   db_name,
                                   headers,
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

        async with client_session_cls(headers=headers) as client_session:
            # spider = spider_cls(request_client=client_session)
            spider_service = spider_service_cls(session=client_session,
                                                spider_cls=spider_cls,
                                                # parse_strategy_factory=None,
                                                result_db_model=result_model_cls,
                                                html_data_model=html_model_cls)
            await spider_service.crawl(test_urls, rules)

    headers = RequestHeader(
        accept="text/html, application/xhtml+xml, application/xml, image/webp, */*",
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",
        cookie=""
    )
    use_db = 'spiderDB'
    db_client = create_client(host='localhost',
                              username='admin',
                              password='root',
                              port=27017,
                              db_name=use_db)
    urls = [
        f"https://www.baidu.com/s?wd=aiohttp&pn={page*10}"
        for page in range(0,20,10)
    ]
    print(urls)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(test_spider_services(
        db_client=db_client,
        db_name=use_db,
        headers=headers.dict(),
        client_session_cls=ClientSession,
        spider_cls=Spider,
        parse_strategy_factory=ParserContextFactory,
        spider_service_cls=HTMLSpiderService,
        result_model_cls=Result,
        html_model_cls=HTMLData,
        test_urls=urls,
        rules=ScrapeRules(
            parsing_pipeline=[],
            max_concurrency=1
        )
    ))
