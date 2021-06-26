""" Models used by crawler components
"""
from pydantic import BaseModel
from typing import Optional, List


class CrawlResult(BaseModel):
    """ Defines a page visited by crawl algorithm
    
    Fields:
        id: int,
        name: Optional[str],
        url: str,
        page_src: str,
        relative_depth: int,
        neighbors: List[int] = []
    """
    # TODO: implement a graph node like structure
    id: int
    name: Optional[str]
    url: str
    page_src: str
    relative_depth: int
    neighbors: List[int] = []

    def __hash__(self):
        return hash(self.__repr__())

    def __str__(self):
        return f"""<CrawlResult id={self.id}" name={self.name} url={self.url} 
                                page_src={self.page_src[:100]} 
                                relative_depth={self.relative_depth}
                                neighbors={self.neighbors}>"""


