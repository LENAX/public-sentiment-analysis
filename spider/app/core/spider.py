from abc import ABC
from typing import Any, List
from .request_client import RequestClient
from ..enums import RequestStatus
from asyncio import TimeoutError

class BaseSpider(ABC):

    def fetch(self, request: Any) -> Any:
        return NotImplemented


class Spider(BaseSpider):

    def __init__(self, request_client: RequestClient):
        self._request_client = request_client
        self._request_status = None
        self._result = ""

    @property
    def result(self):
        return self._result

    @result.setter
    def result(self, value):
        self._result = value

    @property
    def request_status(self):
        return self._request_status

    @request_status.setter
    def request_status(self, value):
        self._request_status = value

    def __repr__(self):
        if len(self._result):
            return f"<Spider request_status={self._request_status} result={self._result[:30]}>"
        else:
            return f"<Spider request_status={self._request_status}>"

    async def fetch(self, url: str, url_params: dict={}) -> str:
        try:
            async with self._request_client.get(url, params=url_params) as response:
                self._request_status = RequestStatus.from_status_code(response.status)
                self._result = await response.text()

        except TimeoutError as e:
            self._request_status = RequestStatus.TIMEOUT

        return self._result
    

if __name__ == "__main__":
    import aiohttp
    import asyncio
    import time

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/537.36'
    }
    cookies = {'cookies_are': 'working'}

    def timeit(func):
        async def process(func, *args, **params):
            if asyncio.iscoroutinefunction(func):
                print('this function is a coroutine: {}'.format(func.__name__))
                return await func(*args, **params)
            else:
                print('this is not a coroutine')
                return func(*args, **params)

        async def helper(*args, **params):
            print('{}.time'.format(func.__name__))
            start = time.time()
            result = await process(func, *args, **params)

            # Test normal function route...
            # result = await process(lambda *a, **p: print(*a, **p), *args, **params)

            print('>>>', time.time() - start)
            return result

        return helper

    @timeit
    async def run_spider(urls, headers, cookies):

        async def gather_with_concurrency(n, *tasks):
            semaphore = asyncio.Semaphore(n)

            async def sem_task(task):
                async with semaphore:
                    return await task
            return await asyncio.gather(*(sem_task(task) for task in tasks))


        async with aiohttp.ClientSession(headers=headers, cookies=cookies) as client:
            spiders = [Spider(request_client=client) for i in range(len(urls))]
            html_pages = await gather_with_concurrency(10, *[spider.fetch(url) for spider, url in zip(spiders, urls)])
        
        return spiders, html_pages

    for MAX_PAGE in range(10, 30, 10):
        asyncio.sleep(1)
        print(f"scraping page: {MAX_PAGE}")
        urls = [
            f"https://www.baidu.com/s?wd=aiohttp&pn=10&oq=aiohttp&tn=baiduhome_pg&ie=utf-8&usm=2&rsv_idx=2&rsv_pq=c21a2e8200000969&rsv_t=1c15pR3lA89tePfSCnFGfYbH62nArYrTq4W%2B1z%2FubD1lIuUVISLRFFhA9lM4M5f2isZs&rsv_page={page}"
            for page in range(MAX_PAGE)
        ]

        spiders, result = asyncio.run(run_spider(urls, headers, cookies))
