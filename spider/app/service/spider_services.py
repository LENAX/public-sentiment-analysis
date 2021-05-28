import aiohttp
from typing import List, Any
from .base_services import BaseSpiderService
from ..models.data_models import (
    RequestHeader,
    URL,
    HTMLData
)
from ..utils import AsyncIterator

""" Defines all spider services

Catalog
1. HTMLSpiderService
    - Scrape static web page and return its content

"""

class HTMLSpiderService(BaseSpiderService):

    def __init__(self, session: aiohttp.ClientSession, html_data_mapper: Any):
        BaseSpiderService.__init__(self)
        self.session = session
        # self.html_data_mapper = html_data_mapper

    async def get(self, data_src: URL) -> None:
        async with self.session.get(data_src.url) as response:
            print("Status:", response.status)
            print("Content-type:", response.headers['content-type'])

            html = await response.text()
            return html

    async def get_many(self, data_src: List[str]) -> None:
        async for url in AsyncIterator(data_src):
            html = await self.get(URL(url=url))
            print(html[:30])


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
