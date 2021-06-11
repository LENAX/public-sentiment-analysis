from abc import ABC
from typing import List



class BaseCrawlingStrategy(ABC):
    """ Base strategy for crawling websites
    """

    async def crawl(self, rules: List[object]):
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

    async def crawl(self, rules: List[object]) -> List[object]:
        return self._crawling_strategy.crawl(rules)
