import asyncio
from uuid import uuid5, NAMESPACE_OID
from functools import partial
from aiohttp import ClientSession
from datetime import datetime
from typing import List, Any, Tuple, Callable, TypeVar
from motor.motor_asyncio import AsyncIOMotorDatabase
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

class HTMLSpiderService(BaseSpiderService):

    def __init__(self, 
                 session: ClientSession,
                 spider: BaseSpider,
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

    async def _throttled_fetch(self, url, params, semaphore) -> Tuple[str, str]:
        async with semaphore:
            return await self._spider.fetch(url, params)

    async def crawl(self, urls: List[str], rules: ScrapeRules) -> None:
        """ Get html data given the data source

        Args: 
            data_src: List[str]
            rules: ScrapeRules
        """
        semaphore = self._semaphore_class(rules.max_concurrency)
        html_pages = await self._coroutine_runner(
            *[self._throttled_fetch(url, rules.request_params, semaphore)
              for url in urls],
            return_exceptions=True)

        result_dt = datetime.now()
        html_data = [
            self._html_data_model(url=page[0], html=page[1], create_dt=result_dt)
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
                 table_id_generator: Callable = partial(uuid5, NAMESPACE_OID)
                ) -> None:
        self._session = session
        self._spider = spider
        self._result_db_model = result_db_model
        self._html_data_model = html_data_model
        self._table_id_generator = table_id_generator

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
                 table_id_generator: Callable = partial(uuid5, NAMESPACE_OID)
                 ) -> None:
        self._session = session
        self._spider_cls = spider_cls
        self._parse_strategy_factory = parse_strategy_factory
        self._result_db_model = result_db_model
        self._html_data_model = html_data_model
        self._table_id_generator = table_id_generator

    async def _throttled_fetch(self, spider, semaphore) -> Tuple[str, str]:
        async with semaphore:
            return await spider.fetch()

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

        # parse links for search results
        # boost parallelism with multiprocessing



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
                                   spider_service_cls,
                                   result_model_cls,
                                   html_model_cls,
                                   test_urls,
                                   rules):
        db = db_client[db_name]
        result_model_cls.db = db
        html_model_cls.db = db

        async with client_session_cls(headers=headers) as client_session:
            spider = spider_cls(request_client=client_session)
            spider_service = spider_service_cls(session=client_session,
                                                spider=spider,
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
        for page in range(0,50)
    ]

    loop = asyncio.get_event_loop()
    loop.run_until_complete(test_spider_services(
        db_client=db_client,
        db_name=use_db,
        headers=headers.dict(),
        client_session_cls=ClientSession,
        spider_cls=Spider,
        spider_service_cls=HTMLSpiderService,
        result_model_cls=Result,
        html_model_cls=HTMLData,
        test_urls=urls,
        rules=ScrapeRules(max_concurrency=5)
    ))
