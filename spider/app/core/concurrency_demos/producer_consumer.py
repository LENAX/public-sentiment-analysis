"""
A simple producer/consumer demo, using Queue.task_done and Queue.join
"""
import aiohttp
import asyncio
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

async def producer(queue, production_requests):
    async def produce_product(product_request, semaphore):
        async def make_one_product(worker, request):
            async with semaphore, worker.get(request.url) as response:
                text = await response.text()
            return text
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/537.36'
        }

        async with aiohttp.ClientSession(headers=headers) as session:
            production_tasks = [asyncio.create_task(make_one_product(session, request))
                                for request in product_request]
            products = await asyncio.gather(*production_tasks)
            return products

    semaphore = asyncio.Semaphore(2)
    
    for i, request in enumerate(production_requests):
        # produce an item 
        print(f"I am producing product {i}")

        # do some io here
        product = await produce_product(request, semaphore)

        # send the item to queue
        await queue.put(product)


async def consumer(queue, consumer_id, process_worker_pool):


    print(f"I am consumer {consumer_id}.")
    loop = asyncio.get_running_loop()
    while True:
       
        # wait for an item from the producer
        item = await queue.get()
        print(len(item))

        # process the item
        print(f"I am consumer {consumer_id}, and I am consuming {len(item)}...")
        # print(partial(parse, text=item[0], rule='//div'))

        # do some io
    
        tasks = [loop.run_in_executor(
                    process_worker_pool, partial(parse, text=text, rule='//h3/a'))
                    for text in item]
        for task in asyncio.as_completed(tasks, loop=loop):
            results = await task
            print(results)

        # notify the queue that the item has been processed
        queue.task_done()


async def run_demo(producer, production_requests, consumer, n_consumers):
    queue = asyncio.Queue()

    # create consumers
    with ProcessPoolExecutor(max_workers=4) as pool:
        consumers = [asyncio.create_task(consumer(queue, consumer_id=i, process_worker_pool=pool))
                    for i in range(n_consumers)]

        # run the producer and wait for completion
        await producer(queue, production_requests)

        # wait until the consumer has processed all items
        await queue.join()

        # kill all consumers waiting for an item
        for consumer in consumers:
            consumer.cancel()

        await asyncio.gather(*consumers, return_exceptions=True)

@dataclass
class WebPage:
    content: str


@dataclass
class ScrapeTask:
    url: str

# create 100 scrape tasks and make them into 10 by 10 groups.
scrape_tasks = [
    [ScrapeTask(url="https://www.baidu.com/s?wd=python&pn={i}") for i in range(group_no*20, (group_no+1)*20, 10)]
    for group_no in range(0, 10)
]

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/537.36'
}
cookies = {'cookies_are': 'working'}

asyncio.run(
    run_demo(producer=producer,
             production_requests=scrape_tasks,
             consumer=consumer,
             n_consumers=2))