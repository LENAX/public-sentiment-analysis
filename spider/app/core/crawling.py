from abc import ABC
from typing import List



class BaseCrawlingStrategy(ABC):
    """ Base strategy for crawling websites
    """

    async def crawl(self, rules: List[ParseRule]) -> List[ParseResult]:
        return NotImplemented
