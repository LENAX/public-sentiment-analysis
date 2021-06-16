import asyncio
import aiohttp
from lxml.html import fromstring
from functools import partial
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from typing import List
import os

@dataclass
class SearchResult:
    title: str
    href: str
    abstract: str
    date: str
    image_urls: List[str]


""" Running a cpu bound task and an io bound task concurrently
"""


def parsing(text):
    # CPU-bound operations will block the event loop:
    # in general it is preferable to run them in a
    # process pool.
    my_pid = os.getpid()
    print(f"My id is: {my_pid}")
    search_result_xpath = "//div[contains(@class, 'result') and contains(@class, 'new-pmd')]"
    title_link_xpath = "//h3/a[not (@class)]"
    abstract_xpath = "//div[contains(@class, 'c-abstract')]"
    datetime_xpath = "//span[contains(@class, '_3wnyfua')]"
    image_src_xpath = "//span[contains(@class, 'c-img-border')]//preceding-sibling::img/@src"

    parsed_text = fromstring(text)
    search_results = parsed_text.xpath(search_result_xpath)
    
    parsed_search_results = []
    for result in search_results:
        title_link = result.xpath(title_link_xpath)
        abstract = result.xpath(abstract_xpath)
        create_dt = result.xpath(datetime_xpath)
        image_srcs = result.xpath(image_src_xpath)

        title, href, abstract_text, create_date, image_sources = "", "", "", None, []
        if len(title_link):
            title = title_link[0].text_content().strip()
            href = title_link[0].get('href')
        
        if len(abstract):
            abstract_text = abstract[0].text_content().strip()
        
        if len(create_dt):
            create_date = create_dt[0].text_content().strip()
        
        for src in image_srcs:
            image_sources.append(str(src))

        parsed_search_results.append(SearchResult(
            title=title, href=href, abstract=abstract_text,
            date=create_date, image_urls=image_sources
        ))
    
    return parsed_search_results


async def http_requests(urls):
    print("doing io")
    async def fetch(request_client, url, semaphore):
        async with semaphore, request_client.get(url) as response:
            result = await response.text()

        return result
    semaphore = asyncio.Semaphore(3)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/537.36'
    }
    async with aiohttp.ClientSession(headers=headers) as request_client:
        concurrent_fetch_tasks = [asyncio.create_task(fetch(request_client, url, semaphore)) for url in urls]
        results = await asyncio.gather(*concurrent_fetch_tasks)

    print(len(results))
    return results



async def main(cpu_bound_task, async_task, **kwargs):
    loop = asyncio.get_running_loop()

    async def parse(text_list):
        with ProcessPoolExecutor() as pool:
            futures = [loop.run_in_executor(pool, partial(cpu_bound_task, text))
                       for text in text_list]
            print(futures)
            result = await asyncio.gather(*futures)
        return result
    # print(urls)
    fetch_results = await async_task(kwargs['urls'])
    parse_results = await parse(fetch_results)

    print(parse_results)
    return parse_results

    # io_results = await async_task(kwargs["urls"])
    # print(len(io_results))


urls=[
    f"https://www.baidu.com/s?wd=asyncio&pn={i*10}"
    for i in range(0, 20)
]

asyncio.run(http_requests(urls))

asyncio.run(
    main(parsing, http_requests, urls=urls)
)
