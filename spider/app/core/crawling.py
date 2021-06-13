from abc import ABC
from typing import List
from .spider import BaseSpider
from asyncio import Queue, LifoQueue, PriorityQueue, coroutine

class BaseCrawlingStrategy(ABC):
    """ Base strategy for crawling websites
    """

    async def crawl(self, rules: List[object], task_control_func: coroutine, **kwargs):
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

    async def crawl(self, rules: List[object],
                    task_control_func: coroutine, **kwargs) -> List[object]:
        return self._crawling_strategy.crawl(rules)


class BFSCrawling(BaseCrawlingStrategy):
    """ Performs Breadth First crawling
    """

    def __init__(self, spider: BaseSpider, task_queue: Queue):
        self._spider = spider
        self._task_queue = task_queue

    @property
    def spider(self) -> BaseSpider:
        return self._spider

    @spider.setter
    def spider(self, new_spider: BaseSpider):
        self._spider = new_spider

    async def crawl(self, rules: List[object],
                    task_control_func: coroutine, **kwargs) -> List[object]:
        pass

    
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

    async def crawl(self, rules: List[object],
                    task_control_func: coroutine, **kwargs) -> List[object]:
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

    async def crawl(self, rules: List[object],
                    task_control_func: coroutine, **kwargs) -> List[object]:
        pass
