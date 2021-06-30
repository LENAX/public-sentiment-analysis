import re
import time
from abc import ABC
from typing import List, Callable, Generator
from .spider import BaseSpider
from asyncio import Queue, LifoQueue, PriorityQueue, QueueEmpty
from ..models.data_models import (
    ParseResult, URL, HTMLData, CrawlResult
)
from ..models.request_models import ParseRule
from .parser import ParserContext, LinkParser
from .exceptions import QueueNotProperlyInitialized
from ..utils import throttled
from .request_client import BaseRequestClient, RequestClient

class BaseCrawlingStrategy(ABC):
    """ Base strategy for crawling websites
    """

    async def crawl(self, rules: List[ParseRule],
                    max_depth: int,
                    url_filter_functions: List[Callable] = [],
                    early_stop_control_func: Callable = lambda **kwargs: True,
                    result_filter_func: Callable = lambda result, **kwargs: result,
                    **kwargs) -> List[ParseResult]:
        return NotImplemented


class CrawlerContext(object):
    """ Holds Crawling strategy classes and allow dynamic selection of crawling strategies """

    def __init__(self, crawling_strategy_cls: BaseCrawlingStrategy, **kwargs):
        self._crawling_strategy = crawling_strategy_cls(**kwargs)

    @property
    def crawling_strategy(self) -> BaseCrawlingStrategy:
        return self._crawling_strategy

    @crawling_strategy.setter
    def crawling_strategy(self, crawling_strategy: BaseCrawlingStrategy) -> None:
        self._crawling_strategy = crawling_strategy

    @property
    def start_url(self):
        return self._crawling_strategy.start_url

    @start_url.setter
    def start_url(self, url):
        self._crawling_strategy.start_url = url

    async def crawl(self, rules: List[ParseRule],
                    max_depth: int,
                    url_filter_functions: List[Callable] = [],
                    early_stop_control_func: Callable = lambda **kwargs: True,
                    result_filter_func: Callable = lambda result, **kwargs: result,
                    **kwargs) -> List[ParseResult]:
        return await self._crawling_strategy.crawl(
                        rules=rules, max_depth=max_depth,
                        early_stop_control_func=early_stop_control_func,
                        url_filter_functions=url_filter_functions,
                        result_filter_func=result_filter_func,
                        **kwargs)


class BFSCrawling(BaseCrawlingStrategy):
    """ Uses a spider to perform Breadth First crawling
    """

    def __init__(self,
                 request_client: BaseRequestClient,
                 spider_class: BaseSpider,
                 parser: ParserContext,
                 start_url: str,
                 url_queue: Queue,
                 web_page_queue: Queue,
                 max_concurrency: int = 50,
                 throttled_fetch: Callable = throttled,
                 re_compile: Callable = re.compile):
        self._request_client = request_client
        self._spider_class = spider_class
        self._parser = parser
        self._start_url = start_url
        self._start_url_pattern = re_compile(start_url)
        self._url_queue = url_queue
        self._web_page_queue = web_page_queue
        self._visited_urls = set()
        self._re_comile = re_compile
        self._max_concurrency = max_concurrency
        self._throttled_fetch = throttled_fetch
        self._init_queue()

    @property
    def spider_class(self) -> BaseSpider:
        return self._spider_class

    @spider_class.setter
    def spider_class(self, new_spider_class: BaseSpider):
        self._spider_class = new_spider_class

    @property
    def start_url(self):
        return self.self._start_url

    @start_url.setter
    def start_url(self, url):
        self._parser.base_url = url
        self._start_url = url
        self._start_url_pattern = self._re_comile(url)
        self._init_queue()

    async def _visit(self, url, depth, path, neighbor_id=None):
        spider = self._spider_class(
            request_client=self._request_client,
            url_to_request=url
        )
        _, result = await spider.fetch()
        node = CrawlResult(
            id=hash(url),
            url=url,
            page_src=result,
            relative_depth=depth
        )

        if neighbor_id:
            node.neighbors.append(neighbor_id)
            
        await self._web_page_queue.put(node)
        self._visited_urls.add(url)
        path.append(node)

    def _init_queue(self):
        # assume queue is empty
        if len(self._start_url):
            self._url_queue.put_nowait((self._start_url, 0))

    def _queue_empty(self) -> bool:
        return self._web_page_queue.empty()

    def _calculate_depth(self, url) -> float:
        """ Calculate depth relative to the start url """
        if self._start_url_pattern.pattern == url:
            return 0
        
        common_root_matched = self._start_url_pattern.search(url)
        if common_root_matched is None:
            # current url has no common root with the start url
            return float('inf')
        else:
            _, end = common_root_matched.span()
            relative_url = url[end:]
            depth = len([s for s in relative_url.split("/")
                         if len(s) > 0])
            return depth

    def _resolve_url_base(self, url):
        """ Use the url until the last slash as base """
        return url[:url.rfind('/')]

    def _links_to_visit(self, parsed_links: List[ParseResult],
                        url_filter_function: Callable,
                        max_depth: int
                       ) -> Generator[List[str], None, None]:
        for link in parsed_links:
            is_unvisited_link = link.value not in self._visited_urls
            link_matches_filter = url_filter_function(link.value)
            not_exceeds_depth = self._calculate_depth(link.value) <= max_depth
            should_visit = (is_unvisited_link and
                            link_matches_filter and
                            not_exceeds_depth)
            if should_visit:
                yield link.value

    def _get_url_filter_or_default(self,
                                   url_filter_functions: List[Callable],
                                   current_depth: int) -> Callable:
        url_filter = None
        try:
            url_filter = url_filter_functions[current_depth]
        except IndexError:
            url_filter = lambda url: True

        return url_filter

    async def crawl(self, rules: List[ParseRule],
                    max_depth: int,
                    url_filter_functions: List[Callable] = [],
                    early_stop_control_func: Callable = lambda **kwargs: True, 
                    result_filter_func: Callable = lambda result, **kwargs: result,
                    **kwargs) -> List[CrawlResult]:
        """ Crawls web pages and extracts urls in breadth-first order
        
        Args:
            rules: List of ParseRules used by parser to extract useful information
            max_depth: maximum depth of url level relative to the provided url
            early_stop_control_func: custom control logic to end crawling loop
            url_filter_functions: list of custom url filtering logic where each function filters one level of url, must takes a str and returns a bool value
            result_filter_func: custom result filtering logic, takes a CrawlResult and returns a bool value

        Returns:
            A list of CrawlResult containing all the web pages visited by the crawler

        Raises:
            QueueNotProperlyInitialized
            QueueEmpty
        """
        try:
            path = []
            current_depth = 0

            # url queue should only contain one element
            if self._url_queue.qsize() > 1:
                raise QueueNotProperlyInitialized("URL queue should only contain start url")

            start_url, depth = self._url_queue.get_nowait()
            await self._visit(start_url, depth, path)
            
            while ((not self._queue_empty()) and 
                   early_stop_control_func(**kwargs)):
                node = await self._web_page_queue.get()
                
                """
                Update parser's url base when the crawler step one level deeper.
                The base url helps the parser to get the correct absolute url when dealing with
                relative urls.
                For example, base url changes from foo.com to foo.com/b when the crawler goes to
                foo.com/b/c. In foo.com/b/c, there is a relative url /d which will be transformed to
                an absolute url foo.com/b/c/d
                """
                self._parser.base_url = self._resolve_url_base(node.url)
                parsed_links = self._parser.parse(node.page_src, rules)
                current_depth = self._calculate_depth(node.url)
                url_filter = self._get_url_filter_or_default(
                    url_filter_functions, current_depth)
                
                batch_visit = []
                for link in self._links_to_visit(parsed_links, url_filter, max_depth):
                    print(link)
                    batch_visit.append(self._visit(
                        link, depth+1, path, node.id))
                        
                await self._throttled_fetch(self._max_concurrency, tasks=batch_visit)
            
            return [node for node in path if result_filter_func(node)]

        except QueueEmpty:
            return path
        except Exception as e:
            print(e)
            raise e


    
class DFSCrawling(BaseCrawlingStrategy):

    def __init__(self, spider: BaseSpider, task_queue: LifoQueue):
        self._spider = spider
        self._task_queue = task_queue

    @property
    def spider(self) -> BaseSpider:
        return self._spider

    @spider.setter
    def spider(self, new_spider: BaseSpider):
        self._spider = new_spider

    async def crawl(self, rules: List[ParseRule],
                    max_depth: int,
                    url_filter_functions: List[Callable] = [],
                    early_stop_control_func: Callable = lambda **kwargs: True,
                    result_filter_func: Callable = lambda result, **kwargs: result,
                    **kwargs) -> List[ParseResult]:
        pass

    
class PrioritizedCrawling(BaseCrawlingStrategy):

    def __init__(self, spider: BaseSpider, task_queue: PriorityQueue):
        self._spider = spider
        self._task_queue = task_queue

    @property
    def spider(self) -> BaseSpider:
        return self._spider

    @spider.setter
    def spider(self, new_spider: BaseSpider):
        self._spider = new_spider

    async def crawl(self, rules: List[ParseRule],
                    max_depth: int,
                    url_filter_functions: List[Callable] = [],
                    early_stop_control_func: Callable = lambda **kwargs: True,
                    result_filter_func: Callable = lambda result, **kwargs: result,
                    **kwargs) -> List[ParseResult]:
        pass


class CrawlerContextFactory(object):
    """ Handles CrawlerContext Creation """

    __crawler_classes__ = {
        'bfs_crawler': BFSCrawling,
        'dfs_crawler': DFSCrawling,
        'prioritized_crawler': PrioritizedCrawling,
    }
    __queues__ = {
        'bfs_crawler': Queue,
        'dfs_crawler': LifoQueue,
        'prioritized_crawler': PriorityQueue
    }
    __default_crawler_cls__ = BFSCrawling
    __crawler_context__ = CrawlerContext

    @property
    def crawler_classes(cls):
        return list(cls.__crawler_classes__.keys())

    @classmethod
    def create(cls,
               crawler_name: str,
               start_url: str,
               spider_class: BaseSpider,
               request_client: BaseRequestClient,
               parser_context: ParserContext,
               **kwargs) -> CrawlerContext:
        crawler_cls = cls.__crawler_classes__.get(
            crawler_name, cls.__default_crawler_cls__)
        queue_class = cls.__queues__[crawler_name]

        ctx = cls.__crawler_context__(
            crawling_strategy_cls=crawler_cls,
            spider_class=spider_class,
            request_client=request_client,
            parser=parser_context,
            start_url=start_url,
            url_queue=queue_class(),
            web_page_queue=queue_class(),
            **kwargs
        )
        return ctx


if __name__ == "__main__":
    import aiohttp
    import asyncio
    from functools import partial
    from .spider import Spider
    from .parser import ParserContextFactory
    from .parse_driver import ParseDriver
    from asyncio import Queue

    async def test_bfs_crawl():

        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/537.36'
        }
        start_url = 'http://www.tianqihoubao.com/'
        url_queue, page_queue = Queue(), Queue()

        def is_weather_page(node: CrawlResult):
            return node.relative_depth == 1

        def location_code_filter(url:str, location_code: str):
            return location_code in url
        
        async with (await RequestClient(headers=headers)) as request_client:   
            crawler_context = CrawlerContextFactory.create(
                'bfs_crawler',
                spider_class=Spider,
                request_client=request_client,
                parser_context=ParserContextFactory.create(
                    'link_parser', base_url=start_url),
                start_url=start_url)       
            result = await crawler_context.crawl(
                rules=[
                    ParseRule(
                        field="area_link",
                        rule="//td/a",
                        rule_type="xpath"
                    )
                ],
                url_filter_functions=[
                    partial(location_code_filter, location_code='420000'),
                ],
                max_depth=2,
                result_filter_func=is_weather_page
            )
            
            print(result)

    asyncio.run(test_bfs_crawl())



