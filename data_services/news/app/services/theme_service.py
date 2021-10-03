from data_services.news.app.rpc.news_spider import NewsSpiderService
from typing import List
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
                    f"Failed to create a new spider task for theme: {theme}, trial: {n_trial} / max_retry")
                
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
            await self._db_model.update_one(query, update_data)
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
        pass

    async def add_many(self, data_list: List[BaseModel]) -> None:
        return NotImplemented

    async def get_one(self, query: dict) -> Theme:
        theme = await self._db_model.get_one(query)
        return theme

    async def update_many(self, query: dict, data_list: List[BaseModel]) -> None:
        pass

    async def delete_many(self, query: dict) -> None:
        pass


if __name__ == "__main__":
    import asyncio
    from devtools import debug
    from ..db import create_client

    async def main():
        db_client = create_client(host='localhost',
                                  username='admin',
                                  password='root',
                                  port=27017,
                                  db_name='test')
        ThemeDBModel.db = db_client['test']
        theme_service = ThemeService(data_model=Theme,
                                     db_model=ThemeDBModel,
                                     news_spider_service=None)

        await theme_service.add_one()
        theme = await theme_service.get_one()

        debug(theme)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
