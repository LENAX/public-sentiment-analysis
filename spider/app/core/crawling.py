from abc import ABC
from typing import List, Callable
from .spider import BaseSpider
from asyncio import Queue, LifoQueue, PriorityQueue, QueueEmpty
from ..models.data_models import (
    ParseRule, ParseResult, URL, HTMLData
)
from .parser import ParserContext, LinkParser

class BaseCrawlingStrategy(ABC):
    """ Base strategy for crawling websites
    """

    async def crawl(self, rules: List[ParseRule],
                    max_depth: int,
                    early_stop_control_func: Callable = lambda **kwargs: True,
                    url_filter_func: Callable = lambda urls: urls,
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
                    early_stop_control_func: Callable = lambda **kwargs: True, 
                    url_filter_func: Callable = lambda urls: urls,
                    result_filter_func: Callable = lambda result, **kwargs: result,
                    **kwargs) -> List[ParseResult]:
        return self._crawling_strategy.crawl(
                    rules, max_depth,
                    early_stop_control_func,
                    url_filter_func,
                    result_filter_func,
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

    @property
    def spider(self) -> BaseSpider:
        return self._spider

    @spider.setter
    def spider(self, new_spider: BaseSpider):
        self._spider = new_spider

    async def _visit(self, url):
        result = await self._spider.visit(url)
        await self._web_page_queue.put(result)
        self._visited_urls.add(url)

    def _queue_empty(self):
        return self._web_page_queue.empty() and self._url_queue.empty()

    async def crawl(self, rules: List[ParseRule],
                    max_depth: int,
                    early_stop_control_func: Callable = lambda **kwargs: True, 
                    url_filter_func: Callable = lambda urls: urls,
                    result_filter_func: Callable = lambda result, **kwargs: result,
                    **kwargs) -> List[ParseResult]:
        try:
            results = []
            current_depth = 0
            start_url = self._url_queue.get_nowait()
            self._visit(start_url)
            await self._url_queue.put(start_url) # make sure the loop runs
            while not (self._queue_empty() and 
                       current_depth > max_depth and
                       early_stop_control_func(**kwargs)):
                url = await self._url_queue.get()
                if url not in self._visited_urls:
                    self._visit(url)
                web_page = await self._web_page_queue.get()
                parsed_links = self._parser.parse(web_page, rules)
                results.extend(parsed_links)
                
                for link in url_filter_func(parsed_links):
                    if link.value not in self._visited_urls:
                        self._visit(link.value)
                
                current_depth += 1
            
            return result_filter_func(results, **kwargs)

        except QueueEmpty:
            return results
        except Exception as e:
            print(e)
            return results


    
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
                    early_stop_control_func: Callable = lambda **kwargs: True,
                    url_filter_func: Callable = lambda urls: urls,
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
                    early_stop_control_func: Callable = lambda **kwargs: True,
                    url_filter_func: Callable = lambda urls: urls,
                    result_filter_func: Callable = lambda result, **kwargs: result,
                    **kwargs) -> List[ParseResult]:
        pass


if __name__ == "__main__":
    import aiohttp
    from .spider import Spider
    from .parser import LinkParser
    from .parse_driver import ParseDriver

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/537.36'
    }
    with aiohttp.ClientSession(headers=headers) as client_session:
        spider = Spider(request_client=client_session)
        crawler_context = CrawlerContext(crawling_strategy=BFSCrawling(
                                         spider=spider,
                                         parser=LinkParser(
                                                parser_driver_class=ParseDriver)))


