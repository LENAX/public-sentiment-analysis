import re
import chardet
from abc import ABC, abstractmethod
from typing import Any, List, Tuple, TypeVar, Callable
from .request_client import BaseRequestClient, RequestClient, AsyncBrowserRequestClient
from ..enums import RequestStatus
from asyncio import TimeoutError
from .parser import ParserContext
from concurrent.futures import ProcessPoolExecutor
import traceback

SpiderInstance = TypeVar("SpiderInstance")

class BaseSpider(ABC):

    @abstractmethod
    def fetch(self, url: str, params: dict = {}):
        return NotImplemented


class Spider(BaseSpider):
    """ Core Spider Class for fetching web pages """

    def __init__(self, request_client: BaseRequestClient, url_to_request: str = "", max_retry: int = 10):
        self._request_client = request_client
        self._request_status = None
        self._url = url_to_request
        self._result = ""
        self._max_retry = max_retry if type(max_retry) is int else 1

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

    @classmethod
    def create_from_urls(cls, urls: List[str], request_client: BaseRequestClient, max_retry: int = 10) -> List[SpiderInstance]:
        return [cls(request_client, url, max_retry) for url in urls]

    def __repr__(self):
        if len(self._result):
            return f"<Spider request_status={self._request_status} result={self._result[:30]}>"
        else:
            return f"<Spider request_status={self._request_status}>"

    def _is_mojibake(self, text: str) -> bool:
        cn_characters = re.findall("[\u2E80-\uFE4F]+", text)
        common_cn_characters = re.findall("[\u4e00-\u9fa5]+", text)
        return (len(cn_characters) == 0 or 
                len(common_cn_characters)/len(cn_characters) < 0.99)
    
    def _fix_mojibake(self, byte_str: bytes, encoding_detector: Callable) -> str:
        detect_result = encoding_detector(byte_str)
        fixed_text = ""
        if detect_result['confidence'] >= 0.9:
            fixed_text = byte_str.decode(
                detect_result['encoding'], errors='replace')
        else:
            for cn_encoding in ['gbk', 'gb2312', 'utf-8']:
                decoded = byte_str.decode(
                    cn_encoding, errors='replace')
                if not self._is_mojibake(decoded):
                    fixed_text = decoded
                    break
        return fixed_text

    async def fetch(self, 
                    url: str = "",
                    params: dict={},
                    encoding_detector: Callable=chardet.detect) -> Tuple[str, str]:
        """ Fetch a web page

        Args:
            url: str
            params: dict, Additional parameters to pass to request

        Returns:
            url
            result
        """
        assert len(self._url) > 0 or len(url) > 0
        url_to_request = url if len(url) > 0 else self._url
        request_completed = False
        n_trial = 0

        while not request_completed and n_trial < self._max_retry:
            try:
                raw_body = b""
                async with self._request_client.get(url=url_to_request, params=params) as response:
                    self._request_status = RequestStatus.from_status_code(response.status)
                    if (self._request_status == RequestStatus.NOT_FOUND or 
                        self._request_status == RequestStatus.FORBIDDEN ):
                        return url_to_request, self._result

                    html_text = await response.text(encoding="utf-8", errors="ignore")
                    
                    # fix garbled text issue
                    if not self._is_mojibake(html_text):
                        self._result = html_text
                    else:
                        raw_body = response._body
                        if raw_body is None:
                            raw_body = await response.read()
                        self._result = self._fix_mojibake(raw_body, encoding_detector)
                        
                if len(self._result) == 0:
                    n_trial += 1
                else:
                    request_completed = True
                        
            except TimeoutError as e:
                n_trial += 1
                traceback.print_exc()
                print(f"Request timed out. Retry: {n_trial}/{self._max_retry}")
                self._request_status = RequestStatus.TIMEOUT
            except Exception as e:
                n_trial += 1
                traceback.print_exc()
                print(f"Error while requesting {url_to_request}, exception: {e}")
                print(f"Retry: {n_trial}/{self._max_retry}")
                self._request_status = RequestStatus.CLIENT_ERROR

        return url_to_request, self._result



if __name__ == "__main__":
    import aiohttp
    import asyncio
    import time
    from .request_client import RequestClient, AsyncBrowserRequestClient

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/537.36'
    }
    cookie_text = """BIDUPSID=C2730507E1C86942858719FD87A61E58;
    PSTM=1591763607; BAIDUID=0145D8794827C0813A767D21ADED26B4:FG=1;
    BDUSS=1jdUJiZUIxc01RfkFTTUtoTXZaSFl1SDlPdEgzeGJGVEhkTDZzZ2ZIZlJSM1ZmSVFBQUFBJCQAAAAAAAAAAAEAAACILlzpAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAANG6TV~Ruk1fek;
    __yjs_duid=1_9e0d11606e81d46981d7148cc71a1d391618989521258; BD_UPN=123253; BCLID_BFESS=7682355843953324419; BDSFRCVID_BFESS=D74OJeC6263c72vemTUDrgjXg2-lavcTH6f3bGYZSp4POsT0C6gqEG0PEf8g0KubxY84ogKK3gOTH4PF_2uxOjjg8UtVJeC6EG0Ptf8g0f5;
    H_BDCLCKID_SF_BFESS=tbu8_IIMtCI3enb6MJ0_-P4DePop3MRZ5mAqoDLbKK0KfR5z3hoMK4-qWMtHe47KbD7naIQDtbonofcbK5OmXnt7D--qKbo43bRTKRLy5KJvfJo9WjAMhP-UyNbMWh37JNRlMKoaMp78jR093JO4y4Ldj4oxJpOJ5JbMonLafD8KbD-wD5LBeP-O5UrjetJyaR3R_KbvWJ5TMC_CDP-bDRK8hJOP0njM2HbMoj6sK4QjShPCb6bDQpFl0p0JQUReQnRm_J3h3l02Vh5Ie-t2ynLV2buOtPRMW20e0h7mWIbmsxA45J7cM4IseboJLfT-0bc4KKJxbnLWeIJIjj6jK4JKDG8ft5OP;
    """
    cookie_strings = cookie_text.replace("\n", "").replace(" ", "").split(";")
    cookies = {}
    for cookie_str in cookie_strings:
        try:
            key, value = cookie_str.split("=")
            cookies[key] = value
        except IndexError:
            print(cookie_str)
        except ValueError:
            print(cookie_str)

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

        async with (await AsyncBrowserRequestClient(headers=headers, cookies=cookies)) as client:
            spiders: BaseSpider = Spider.create_from_urls(urls, client)
            print(spiders)
            html_pages = await gather_with_concurrency(2, *[spider.fetch() for spider in spiders])
            print(html_pages)
        
        return spiders, html_pages

    # for MAX_PAGE in range(10, 10, 10):
    # time.sleep(1)
    # print(f"scraping page: {MAX_PAGE}")
    
    urls = [
        "https://voice.baidu.com/act/newpneumonia/newpneumonia/?from=osari_aladin_banner&city=%E5%B9%BF%E4%B8%9C-%E5%B9%BF%E5%B7%9E",
        f"https://new.qq.com/omn/20210618/20210618A08QBO00.html",
        'http://dy.163.com/article/GCS0NEHD0550AXYG.html',
        'https://new.qq.com/omn/20210618/20210618V0DUNT00.html'
    ]

    spiders, result = asyncio.run(run_spider(urls, headers, cookies))
    print(result)
