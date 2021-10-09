import asyncio
from typing import Callable
import aiohttp
import logging
from logging import Logger


def create_logger():
    logging.basicConfig(format="%(asctime)s | %(levelname)s | %(funcName)s | %(message)s",
                        datefmt="%Y-%m-%dT%H:%M:%S")
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    return logger


async def do_post_request(url: str, data: dict, logger: Logger = create_logger()):
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data) as response:
            resp_json = await response.json()
            logger.info(f"Received response: {resp_json}")
    return resp_json


async def run_crawling_task(spider_service_url: str, params: dict,
                            request_func: Callable = do_post_request,
                            logger: Logger = create_logger()):
    result = await request_func(spider_service_url, params, logger=logger)
    logger.info(f"result: {result}")
    return result

if __name__ == "__main__":
    import sys
    sys.path.append("..")

    from .common.db.client import create_client
    from data_services.news.app.models.db_models import ThemeDBModel
    from .config import config
    
    client = create_client(**config['db'])
    ThemeDBModel.db = client[config['db']['db_name']]
    
    async def main(theme_model):
        logger = create_logger()
        theme_list = await theme_model.get({})
        
        news_spider_url = "http://0.0.0.0:5002/baidu-news-spider/crawl-task"
        news_spider_params = {
            'url': 'http://www.baidu.com/s?tn=news&ie=utf-8',
            'past_days': 7,
            'area_keywords': [],
            'theme_keywords': [],
            'epidemic_keywords': []
        }
        
        for theme in theme_list:
            news_spider_params['area_keywords'] = theme.areaKeywords
            news_spider_params['theme_keywords'] = [kw.dict() for kw in theme.themeKeywords]
            news_spider_params['epidemic_keywords'] = theme.epidemicKeywords
            news_spider_params['theme_id'] = theme.themeId
            
            news_crawl_task = run_crawling_task(news_spider_url, news_spider_params, logger=logger)
            result = await asyncio.gather(*[news_crawl_task], return_exceptions=True)
            logger.info(f"result: {result}")
            
            await asyncio.sleep(2)
            
        client.close()
        logger.info("Done!")
        
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(ThemeDBModel))

            
