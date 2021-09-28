import aiohttp
import asyncio
import logging
import ujson
import traceback
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


async def run_migration_index_spider(mode: str = 'update', logger=logger):
    try:
        async with aiohttp.ClientSession(json_serialize=ujson.dumps) as session:
            async with session.post('/migration-index-spider/crawl-task',
                                    json={
                                        "url": "https://huiyan.baidu.com/migration/historycurve.json",
                                        "mode": mode
                                    }) as resp:
                resp_data = await resp.json()
                logger.info(resp_data)
    except Exception as e:
        traceback.print_exc()
        logger.error(e)
        raise e
            

async def run_migration_rank_spider(mode: str = 'update', logger=logger):
    try:
        yesterday = datetime.now() - timedelta(days=1)
        
        async with aiohttp.ClientSession(json_serialize=ujson.dumps) as session:
            async with session.post('/migration-index-spider/crawl-task',
                                    json={
                                        "url": "https://huiyan.baidu.com/migration/provincerank.jsonp",
                                        "mode": mode,
                                        "start_date": yesterday.strftime("%Y-%m-%d"),
                                        "end_date": datetime.now().strftime("%Y-%m-%d")
                                    }) as resp:
                resp_data = await resp.json()
                logger.info(resp_data)
    except Exception as e:
        traceback.print_exc()
        logger.error(e)
        raise e


async def main(args, logger=logger):
    try:
        logger.info("Start running migration index spider...")
        await asyncio.gather(*[
            run_migration_index_spider(args.mode),
            run_migration_rank_spider(args.mode),
        ], return_exceptions=True)
        logger.info("Done!")
    except Exception as e:
        traceback.print_exc()
        logger.error(e)
        raise e


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Run spider scheduled task.')
    parser.add_argument('--mode', default='update', type=str,
                        help='work mode of the spider')
    args = parser.parse_args()
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(args))

