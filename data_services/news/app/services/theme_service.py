from data_services.news.app.models.data_models.theme import Keyword
from data_services.news.app.rpc.models.spider_args import BaiduNewsSpiderArgs
from data_services.news.app.rpc.news_spider import NewsSpiderService
from typing import List, Optional
from pydantic import BaseModel
from .base import BaseAsyncCRUDService
from ..models.db_models import ThemeDBModel
from ..models.data_models import Theme
import pandas as pd
import traceback
import logging
from logging import Logger

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(funcName)s | %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class ThemeService(BaseAsyncCRUDService):
    """ Provides Theme Data Access
    """

    def __init__(self,
                 data_model: Theme,
                 db_model: ThemeDBModel,
                 news_spider_service: NewsSpiderService,
                 logger: Logger = logger):
        self._data_model = data_model
        self._db_model = db_model
        self._news_spider_service = news_spider_service
        self._logger = logger


    async def _create_spider_task(self, theme: Theme, mode: str, max_retry:int = 10) -> bool:
        n_trial = 0
        spider_task_created = False
        
        while not spider_task_created and n_trial < max_retry:
            spider_task_created = await self._news_spider_service.crawl(theme, mode=mode)
            if spider_task_created:
                self._logger.info(f"Successfully created a new spider task for theme: {theme}")
            else:
                self._logger.info(
                    f"Failed to create a new spider task for theme: {theme}, trial: {n_trial} / {max_retry}")
                
        return spider_task_created
    
    async def add_one(self, data: Theme) -> None:
        try:
            theme = await self._db_model.get_one({'themeId': data.themeId})
            
            if theme is not None:
                return
            
            await self._db_model.parse_obj(data).save()
            spider_task_created = await self._create_spider_task(data, mode='history')
            
            if not spider_task_created:
                self._logger.error("Failed to create a new spider task! Max retry exceeded.")
                
        except Exception as e:
            traceback.print_exc()
            self._logger.error(e)
            
    async def update_one(self, query: dict, update_data: Theme) -> None:
        try:
            await self._db_model.update_one(query, update_data.dict())
            spider_task_created = await self._create_spider_task(update_data, mode='update')

            if not spider_task_created:
                self._logger.error("Failed to create a new spider task! Max retry exceeded.")
        except Exception as e:
            traceback.print_exc()
            self._logger.error(e)
    
    async def delete_one(self, query: dict) -> None:
        try:
            await self._db_model.delete_one(query)
        except Exception as e:
            traceback.print_exc()
            self._logger.error(e)
    
    async def get_many(self, query: dict, page_size: int = 0, page_number: int = 0) -> List[Theme]:
        """
        """
        try:
            await self._db_model.get(query, limit=page_size, skip=page_size* page_number)
        except Exception as e:
            traceback.print_exc()
            self._logger.error(e)

    async def add_many(self, data_list: List[BaseModel]) -> None:
        return NotImplemented

    async def get_one(self, query: dict) -> Optional[Theme]:
        theme = await self._db_model.get_one(query)
        if theme:
            return self._data_model.parse_obj(theme)
        else:
            return None

    async def update_many(self, query: dict, data_list: List[BaseModel]) -> None:
        pass

    async def delete_many(self, query: dict) -> None:
        pass


if __name__ == "__main__":
    import asyncio
    from devtools import debug
    from ..db.client import create_client
    from data_services.news.app.rpc.request_client.request_client import RequestClient

    async def main():
        db_client = create_client(host='localhost',
                                  username='admin',
                                  password='root',
                                  port=27017,
                                  db_name='test')
        ThemeDBModel.db = db_client['test']
        async with (await RequestClient()) as client_session:
            news_spider_service = NewsSpiderService(
                remote_service_endpoint='http://localhost:5002/baidu-news-spider/crawl-task',
                request_client=client_session,
                request_model=BaiduNewsSpiderArgs
            )
            theme_service = ThemeService(data_model=Theme,
                                         db_model=ThemeDBModel,
                                         news_spider_service=news_spider_service)

            new_theme = Theme(themeId=0,
                            areaKeywords=['湖北省', '武汉', '荆门'],
                            themeKeywords=[
                                Keyword(keywordType=1, keyword='境外输入'),
                                Keyword(keywordType=0, keyword='疫苗接种'),],
                            epidemicKeywords=['新型冠状肺炎'])
            await theme_service.add_one(new_theme)
            theme = await theme_service.get_one({'themeId': 0})

            debug(theme)
            
            updated_theme = Theme(themeId=0,
                                areaKeywords=['湖北省', '武汉', '荆门', '黄石市'],
                                themeKeywords=[
                                    Keyword(keywordType=1, keyword='境外输入'),
                                    Keyword(keywordType=0, keyword='疫苗接种'),
                                    Keyword(keywordType=0, keyword='德尔塔型'), ],
                                epidemicKeywords=['新型冠状肺炎'])
            
            await theme_service.update_one({'themeId': 0}, updated_theme)
            theme = await theme_service.get_one({'themeId': 0})

            debug(theme)
            
            await theme_service.delete_one({'themeId': 0})
            theme = await theme_service.get_one({'themeId': 0})

            debug(theme)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
