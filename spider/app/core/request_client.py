from abc import ABC, abstractmethod
from aiohttp import ClientSession
from typing import (
    Any, Callable, TypeVar, Generator, List, Union,
    Optional, Type
)
from pyppeteer.launcher import launch
from asyncinit import asyncinit
from contextlib import contextmanager, asynccontextmanager
from functools import partial

Response = TypeVar("Response")
ResponseContext = TypeVar("ResponseContext")
TracebackType = TypeVar("TracebackType")

class BaseRequestClient(ABC):
    """ Base class all request client classes
    """

    @abstractmethod
    def get(self, url: str, params: dict = {}) -> Any:
        return NotImplemented


@asyncinit
class RequestClient(BaseRequestClient):
    """ Handles HTTP Request and Connection Pooling
    """
    
    async def __init__(self,
                 headers: dict = {},
                 cookies: dict = {},
                 client_class: ClientSession = ClientSession,):
        self._client = client_class(headers=headers, cookies=cookies)

    @contextmanager
    def get(self, url: str, params: dict = {}) -> ResponseContext:
        return self._client.get(url=url, params=params)

    async def __aenter__(self) -> "ClientSession":
        return self._client

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        await self._client.close()
        
    async def close(self):
        await self._client.close()


@asyncinit
class AsyncBrowserRequestClient(BaseRequestClient):
    """ Handles HTTP Request with a browser
    """

    async def __init__(self,
                 browser_launcher: Callable = launch,
                 browser_path: str = None,
                 headless: bool = True,
                 headers: dict = {},
                 cookies: List[dict] = []):
        self._browser = await browser_launcher(
            browser_path=browser_path,
            headless=headless)
        self._headers = headers
        self._cookies = cookies

    @property
    def headers(self):
        return self._headers

    @headers.setter
    def headers(self, new_headers: dict):
        self._headers = new_headers

    @property
    def cookies(self):
        return self._cookies

    @cookies.setter
    def cookies(self, new_cookies: dict):
        self._cookies = new_cookies

    async def _patch_response(self, response: Response, js_evaluator: Callable):
        """ Make response seems identical to the one returned from RequestClient

        The response object returned from RequestClient is from aiohttp library,
        while this one is from pyppeteer. We have to do some monkey-patching to make
        them look identical to the client code.
        """
        async def patched_text(text, encoding="", errors=""):
            return text

        evaluated_text = await js_evaluator()
        raw_body = await response.buffer()
        response._body = raw_body
        response.text = partial(patched_text, text=evaluated_text)

    def _to_cookie_list(self, cookies: dict, url: str):
        return [{"name": key, "value": cookies[key], "url": url} for key in cookies]

    @asynccontextmanager
    async def get(self, 
                  url: str,
                  params: dict = {}) -> Generator[str, dict, Response]:
        if type(self._cookies) is dict:
            self._cookies = self._to_cookie_list(self._cookies, url)
        
        page = await self._browser.newPage()
        await page.setCookie(*self._cookies)
        await page.setExtraHTTPHeaders(self._headers)

        try:
            response = await page.goto(url)
            # add js evaluation ability to response.text method
            await self._patch_response(response, page.content)
            yield response
        except Exception as e:
            print(e)
        finally:
            await page.close()

    async def close(self):
        await self._browser.close()

    async def __aenter__(self) -> "AsyncBrowserRequestClient":
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        await self._browser.close()



if __name__ == "__main__":
    import asyncio
    from typing import List
    from pyquery import PyQuery as pq

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/537.36'
    }

    def get_cookies():
        cookie_text = """BIDUPSID=C2730507E1C86942858719FD87A61E58;
        PSTM=1591763607; BAIDUID=0145D8794827C0813A767D21ADED26B4:FG=1;
        BDUSS=1jdUJiZUIxc01RfkFTTUtoTXZaSFl1SDlPdEgzeGJGVEhkTDZzZ2ZIZlJSM1ZmSVFBQUFBJCQAAAAAAAAAAAEAAACILlzpAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAANG6TV~Ruk1fek;
        __yjs_duid=1_9e0d11606e81d46981d7148cc71a1d391618989521258; BD_UPN=123253; BCLID_BFESS=7682355843953324419; BDSFRCVID_BFESS=D74OJeC6263c72vemTUDrgjXg2-lavcTH6f3bGYZSp4POsT0C6gqEG0PEf8g0KubxY84ogKK3gOTH4PF_2uxOjjg8UtVJeC6EG0Ptf8g0f5;
        H_BDCLCKID_SF_BFESS=tbu8_IIMtCI3enb6MJ0_-P4DePop3MRZ5mAqoDLbKK0KfR5z3hoMK4-qWMtHe47KbD7naIQDtbonofcbK5OmXnt7D--qKbo43bRTKRLy5KJvfJo9WjAMhP-UyNbMWh37JNRlMKoaMp78jR093JO4y4Ldj4oxJpOJ5JbMonLafD8KbD-wD5LBeP-O5UrjetJyaR3R_KbvWJ5TMC_CDP-bDRK8hJOP0njM2HbMoj6sK4QjShPCb6bDQpFl0p0JQUReQnRm_J3h3l02Vh5Ie-t2ynLV2buOtPRMW20e0h7mWIbmsxA45J7cM4IseboJLfT-0bc4KKJxbnLWeIJIjj6jK4JKDG8ft5OP;
        """
        cookie_strings = cookie_text.replace("\n", "").replace(" ", "").split(";")
        cookies = []
        for cookie_str in cookie_strings:
            try:
                key, value = cookie_str.split("=")
                cookie = {'domain': "www.baidu.com"}
                cookie['name'] = key
                cookie['value'] = value
                cookies.append(cookie)
            except IndexError:
                print(cookie_str)
            except ValueError:
                print(cookie_str)
        print(cookies)
        return cookies

    async def test_browser_client(urls: List[str],
                                  headers: dict = {}, 
                                  cookies: List[dict]= []):
        async def fetch(request_client, url, params):
            async with request_client.get(url=url, params=params) as response:
                result = await response.text()
                return result
        
        # browser_client = await AsyncBrowserRequestClient(headless=False,
        #                                                  headers=headers, 
        #                                                  cookies=cookies)
        async with (await AsyncBrowserRequestClient(headless=False,
                                                    headers=headers,
                                                    cookies=cookies)) as browser_client:
            async with browser_client.get(url=urls[0]) as response:
                result = await response.text()
                doc = pq(result)
                epidemic_summary = doc(
                    ".ProvinceSummary_1-1-306_3Zia33").text()
                print(epidemic_summary)
            
            # page_texts = await asyncio.gather(*[fetch(browser_client, url, {})
            #                                     for url in urls])
            # for page_text in page_texts:
            #     doc = pq(page_text)
            #     epidemic_summary = doc(".ProvinceSummary_1-1-306_3Zia33").text()
            #     print(epidemic_summary)
            # await browser_client.close()
            # return page_texts

    urls = [
        "https://voice.baidu.com/act/newpneumonia/newpneumonia/?from=osari_aladin_banner&city=%E5%B9%BF%E4%B8%9C-%E5%B9%BF%E5%B7%9E",
        "https://new.qq.com/omn/20210618/20210618A08QBO00.html",
        'http://dy.163.com/article/GCS0NEHD0550AXYG.html',
        'https://new.qq.com/omn/20210618/20210618V0DUNT00.html'
    ]
    asyncio.run(test_browser_client(urls, headers=headers, cookies=get_cookies()))
