import aiohttp
from datetime import datetime
from typing import List, Any
from .base_services import BaseSpiderService, BaseServiceFactory
from ..models.data_models import (
    RequestHeader,
    URL,
    HTMLData,
)
from ..models.request_models import ScrapeRules
from ..enums import JobType
from ..utils import AsyncIterator

""" Defines all spider services

Catalog
1. HTMLSpiderService
    - Scrape static web page and return its content

"""

SPIDER_TYPES = {
    JobType.BASIC_PAGE_SCRAPING: HTMLSpiderService,
    JobType.SEARCH_RESULT_AGGREGATION: SearchResultSpider
}

class HTMLSpiderService(BaseSpiderService):

    def __init__(self, session: aiohttp.ClientSession, job_id: str = None):
        BaseSpiderService.__init__(self)
        self.session = session
        self.html_data: List[HTMLData] = []
        self.job_id = job_id
        self.page_count = 0

    async def get(self, data_src: URL) -> None:
        async with self.session.get(data_src.url) as response:
            html = await response.text()
            return html

    async def get_many(self, data_src: List[str], rules: ScrapeRules,
                       callback: Callable = None, async_db_action: Callable = None,
                       **kwargs) -> None:
        """ Get html data given the data source

        Args: 
            data_src: List[str]
            rules: ScrapeRules
            callback: callback function for handling tasks after scraping completes
            async_db_action: coroutine for handling database operations
            kwargs: arguments for callbacks
        """
        self.html_data = []
        async for url in AsyncIterator(data_src):
            target_url = URL(url=url)
            html = await self.get(target_url)
            html_data = HTMLData(url=target_url, html=html,
                                 create_dt=datetime.now(),
                                 job_id=self.job_id)
            self.page_count += 1
            self.html_data.append(html_data)

        if callback:
            callback(**kwargs)
        
        if async_db_action:
            await async_db_action(data=self.html_data, **kwargs)
            
        return self.html_data



class SearchResultSpider(BaseSpiderService):

    def __init__(self, session: aiohttp.ClientSession, html_data_mapper: Any):
        pass


class WebSpider(BaseSpiderService):

    def __init__(self, session: aiohttp.ClientSession, html_data_mapper: Any):
        pass


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

    async def test_main():
        headers = RequestHeader(
            accept="text/html, application/xhtml+xml, application/xml, image/webp, */*",
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36",
            cookie=""
        )
        async with aiohttp.ClientSession(headers=dict(headers)) as sess:
            html_spider = HTMLSpiderService(session=sess, headers=headers, html_data_mapper=None)
            html = await html_spider.get(data_src=URL(url="https://www.baidu.com"))
        print(html[:100])

    loop = asyncio.get_event_loop()
    loop.run_until_complete(test_main())
