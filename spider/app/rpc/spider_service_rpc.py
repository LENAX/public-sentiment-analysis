import aiohttp
from typing import List
import logging
from functools import partial

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(funcName)s |%(message)s",
                    datefmt="%Y-%m-%dT%H:%M:%S%z")
spider_rpc_logger = logging.getLogger(__name__)
spider_rpc_logger.setLevel(logging.DEBUG)


async def run_crawling_task(urls: List[str] = [], port: int = 8000, endpoint: str = '/spider/crawl-task', logger=spider_rpc_logger):
    """ Use RPC to mitigate the unserializable task issue
    
    If you try to serialize a crawling task, you will fail because the browser controller object
    used by the spider is not serializable. Instead, you can use this method to indirectly schedule
    a crawling task.
    """
    async with aiohttp.ClientSession() as session:
        async with session.post(
            f'http://0.0.0.0:8000/spider/crawl-task',
            json=urls
        ) as response:
            resp_json = await response.json()
            logger.info(f"received response: {resp_json}")
            

async def fetch_historical_report(url: str, start_date: str, end_date: str,
                                  port: int = 8000, endpoint: str = '/spider/historical-data', logger=spider_rpc_logger):
    """ Fetch historical COVID-19 daily report (provincial level)
    """
    params = {
        "url": url, "start_date": start_date, "end_date": end_date
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f'http://0.0.0.0:8000/spider/historical-data',
            params=params
        ) as response:
            resp_json = await response.json()
            logger.info(f"received response: {resp_json}")
            

def spider_rpc_wrapper(port: int = 8000, endpoint: str = '/spider/crawl-task'):
    return partial(run_crawling_task, port=port, endpoint=endpoint)
            

if __name__ == "__main__":
    import argparse
    import asyncio
    from datetime import datetime
    from dateutil import parser
    
    loop = asyncio.get_event_loop()
    parser = argparse.ArgumentParser(description='Run spider tasks')
    parser.add_argument('--task', type=str, default='daily')
    parser.add_argument('--startDate', type=str, default='2020-01-21')
    parser.add_argument('--endDate', type=str, default=datetime.now().strftime('%Y-%m-%d'))

    args = parser.parse_args()
    
    if args.task == 'daily':
        loop.run_until_complete(run_crawling_task(
            urls=['https://ncov.dxy.cn/ncovh5/view/pneumonia']))
        spider_rpc_logger.info("Daily report crawling completed!")
    elif args.task == 'history':
        loop.run_until_complete(fetch_historical_report(
            url='https://ncov.dxy.cn/ncovh5/view/pneumonia',
            start_date=args.startDate,
            end_date=args.endDate))
        spider_rpc_logger.info("Historical report crawling completed!")
    else:
        spider_rpc_logger.info("Unrecognized task.")
