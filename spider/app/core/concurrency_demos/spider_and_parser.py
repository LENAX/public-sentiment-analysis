""" A special case of Producer Consumer model

In this case, spider takes url input from URL queue and sends downloaded data to HTML Queue.
On the other hand, parser takes HTML Queue and sends parsed html back to URL queue.
When both spider and parser are waiting for each other, the loop ends.
"""
import aiohttp
import asyncio
from asyncio import Queue
from os import cpu_count
from functools import partial
from lxml.html import fromstring
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass


def with_semaphore(value=1):
    def semaphore_decorator(func):
        async def wrapper(*args, **kwargs):
            if asyncio.iscoroutinefunction(func):
                async with asyncio.Semaphore(value):
                    return await func(*args, **kwargs)
            else:
                print('this is not a coroutine')
                return func(*args, **kwargs)
        return wrapper
    return semaphore_decorator


def parse(text, rule):
    parsed_text = fromstring(text)
    selected_elements = parsed_text.xpath(rule)

    return [element.text_content() for element in selected_elements]


def url_parser(text, rule):
    print("!!")
    if len(text) == 0:
        return []

    parsed_text = fromstring(text)
    selected_links = parsed_text.xpath(rule)
    links = []
    for element in selected_links:
        url = element.get('href')
        if url and url.startswith('http'):
            links.append(url)

    return links


async def spider(url_queue: Queue, html_queue: Queue,
                 max_depth: int, max_concurrent_fetch: int = 5):
    async def fetch(client_session, url, semaphore):
        async with client_session.get(url) as response:
            text = await response.text()
        return text

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/537.36'
    }
    semaphore = asyncio.Semaphore(max_concurrent_fetch)

    async with aiohttp.ClientSession(headers=headers) as session:
        for i in range(max_depth):
            print(f"Current iteration: {i}")
            print(f"waiting for url_queue, size: {url_queue.qsize()}")
            urls = await url_queue.get()
            print(f"fetched {len(urls)} urls")
            fetch_tasks = [asyncio.create_task(fetch(session, url, semaphore))
                           for url in urls if url.startswith("http")]
            html_pages = await asyncio.gather(*fetch_tasks)
            print(f"fetched {len(html_pages)} pages")
            url_queue.task_done()
            await html_queue.put(html_pages)


async def parser(url_queue: Queue, html_queue: Queue, parsing_func, executor_pool: ProcessPoolExecutor, max_iteration: int):
    loop = asyncio.get_event_loop()

    for i in range(max_iteration):
        # wait for an item from the producer
        print(f"Current iteration: {i}")
        print(f"waiting for html_queue, size: {html_queue.qsize()}.")
        print(f"url_queue, size: {url_queue.qsize()}.")
        html_pages = await html_queue.get()
        print(f"Retrieved {len(html_pages)} page from queue.")
        
        if len(html_pages) == 0:
            continue
        
        tasks = [loop.run_in_executor(
                    executor_pool, 
                    partial(parsing_func, text=page, rule='//h3/a'))
                for page in html_pages]
        # print(tasks)
        for parsing_task in asyncio.as_completed(tasks, loop=loop):
            # print(parsing_task)
            results = await parsing_task
            print(results)
            await url_queue.put(results)
            print(f"url_queue, size: {url_queue.qsize()}.")
            print(f"html_queue, size: {html_queue.qsize()}.")

        # notify the queue that the item has been processed
        html_queue.task_done()       


async def detect_deadlock(url_queue, html_queue, deadlock_event):
    while True:
        await asyncio.sleep(0.1)
        is_deadlock = url_queue.qsize() == 0 and html_queue.qsize() == 0
        if is_deadlock:
            deadlock_event.set()



async def run_crawling(spider, parser, parsing_func, deadlock_monitor, start_urls, max_depth, max_concurrent_fetch):
    url_queue, html_queue = asyncio.Queue(), asyncio.Queue()
    url_queue.put_nowait(start_urls)
    deadlock_event = asyncio.Event()
    loop = asyncio.get_event_loop()

    # create consumers
    with ProcessPoolExecutor(max_workers=4) as pool:
        spider_task = asyncio.create_task(
            spider(url_queue, html_queue, max_depth, max_concurrent_fetch))
        parse_task = asyncio.create_task(
            parser(url_queue, html_queue, parsing_func, pool, max_depth))
        deadlock_monitoring_task = asyncio.create_task(
            deadlock_monitor(url_queue, html_queue, deadlock_event))
        await asyncio.gather(*[spider_task, parse_task, deadlock_monitoring_task])
        await deadlock_event.wait()
        print("deadlock!")




# create 100 scrape tasks and make them into 10 by 10 groups.
# scrape_tasks = [
#     [f"https://www.baidu.com/s?wd=asyncio&pn={i}"
#      for i in range(group_no*20, (group_no+1)*20, 10)]
#     for group_no in range(0, 10)
# ]

# headers = {
#     'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/537.36'
# }
# cookies = {'cookies_are': 'working'}

asyncio.run(
    run_crawling(spider=spider,
                 parser=parser,
                 parsing_func=url_parser,
                 deadlock_monitor=detect_deadlock,
                 start_urls=[
                    f"https://www.baidu.com/s?wd=asyncio&pn={i*10}"
                    for i in range(3)],
                 max_depth=3,
                 max_concurrent_fetch=100))
