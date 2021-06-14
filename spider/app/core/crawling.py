from abc import ABC
from typing import List, Callable
from .spider import BaseSpider
from asyncio import Queue, LifoQueue, PriorityQueue, QueueEmpty
from ..models.data_models import (
    ParseRule, ParseResult, URL, HTMLData, CrawlResult
)
from .parser import ParserContext, LinkParser
from .exceptions import QueueNotProperlyInitialized


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

    def __init__(self, crawling_strategy: BaseCrawlingStrategy):
        self._crawling_strategy = crawling_strategy

    @property
    def crawling_strategy(self) -> BaseCrawlingStrategy:
        return self._crawling_strategy

    @crawling_strategy.setter
    def crawling_strategy(self, crawling_strategy: BaseCrawlingStrategy) -> None:
        self._crawling_strategy = crawling_strategy

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

    def __init__(self, spider: BaseSpider, parser: LinkParser,
                 start_url: str, url_queue: Queue, web_page_queue: Queue):
        self._spider = spider
        self._parser = parser
        self._start_url = start_url
        self._url_queue = url_queue
        self._web_page_queue = web_page_queue
        self._visited_urls = set()
        self._init_queue()

    @property
    def spider(self) -> BaseSpider:
        return self._spider

    @spider.setter
    def spider(self, new_spider: BaseSpider):
        self._spider = new_spider

    async def _visit(self, url, depth, path, neighbor_id=None):
        result = await self._spider.fetch(url)
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
        self._url_queue.put_nowait((self._start_url, 0))

    def _queue_empty(self) -> bool:
        return self._web_page_queue.empty()

    def _calculate_depth(self, url):
        """ Calculate depth relative to the start url """
        pass

    def _resolve_url_base(self, url):
        """ Use the url until the last slash as base """
        return url[:url.rfind('/')]

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
            
            while (current_depth < max_depth and
                   (not self._queue_empty()) and 
                   early_stop_control_func(**kwargs)):
                node = await self._web_page_queue.get()
                # update parser's url base when the crawler step one level deeper
                self._parser.base_url = self._resolve_url_base(node.url)
                parsed_links = self._parser.parse(node.page_src, rules)
                links_to_visit = [link.value for link in parsed_links
                                  if link.value not in self._visited_urls]
                
                if current_depth < len(url_filter_functions):
                    links_to_visit = [link for link in links_to_visit if url_filter_functions[depth](link)]

                batch_visit = [asyncio.create_task(self._visit(link, depth+1, path, node.id))
                               for link in links_to_visit]
                await asyncio.gather(*batch_visit)

                current_depth += 1
            
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


if __name__ == "__main__":
    import aiohttp
    import asyncio
    from functools import partial
    from .spider import Spider
    from .parser import LinkParser
    from .parse_driver import ParseDriver
    from asyncio import Queue

    async def test_bfs_crawl():

        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/537.36'
        }
        start_url = 'http://www.tianqihoubao.com/'
        url_queue, page_queue = Queue(), Queue()
        semaphore = asyncio.Semaphore(200)

        def is_weather_page(node: CrawlResult):
            return node.relative_depth == 1

        def location_code_filter(url:str, location_code: str):
            return location_code in url
        
        async with semaphore, aiohttp.ClientSession(headers=headers) as client_session:
            spider = Spider(request_client=client_session)
            crawler_context = CrawlerContext(crawling_strategy=BFSCrawling(
                                            spider=spider,
                                            parser=LinkParser(
                                                parse_driver_class=ParseDriver,
                                                base_url=start_url),
                                            start_url=start_url,
                                            url_queue=url_queue,
                                            web_page_queue=page_queue))
            
            
            result = await crawler_context.crawl(
                rules=[
                    ParseRule(
                        field="area_link",
                        rule="//td/a",
                        rule_type="xpath"
                    )
                ],
                url_filter_functions=[
                    partial(location_code_filter, location_code='420000')
                ],
                max_depth=2,
                result_filter_func=is_weather_page
            )
            
            print(result)

    asyncio.run(test_bfs_crawl())



