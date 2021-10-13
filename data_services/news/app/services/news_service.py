import logging
import traceback
from logging import Logger
from typing import List

import pandas as pd
from pydantic import BaseModel

from ..models.data_models import News
from ..models.db_models import NewsDBModel
from .base import BaseAsyncCRUDService

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(funcName)s | %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class NewsService(BaseAsyncCRUDService):
    """ Provides News Data Access
    """

    def __init__(self,
                 data_model: News,
                 db_model: NewsDBModel,
                 logger: Logger = logger):
        self._data_model = data_model
        self._db_model = db_model
        self._logger = logger
        
    def _to_dataframe(self, data: List[BaseModel]):
        data_list = [d.dict() for d in data]
        return pd.DataFrame(data_list)

    def _remove_duplicates(self, df, sort_columns: List[str], unique_columns: List[str]):
        return df.sort_values(by=sort_columns).drop_duplicates(
            subset=unique_columns, keep='last')
        
    def _unique(self, news_list: List[NewsDBModel]):
        news_df = self._to_dataframe(news_list)
        unique_news_df = self._remove_duplicates(
            news_df, sort_columns=['create_dt'], unique_columns=['summary'])
        return [self._db_model.parse_obj(record) for record in unique_news_df.to_dict(orient='records')]

    async def get_many(self, query: dict, page_size: int = 0, page_number: int = 0) -> List[News]:
        """ Get the most recent aqi report for db
        """
        try:
            # TODO: remove duplicate entries
            limit = page_size
            skip = page_size * page_number
            news_list: List[NewsDBModel] = await self._db_model.get(query, limit=limit, skip=skip)
            
            return [self._data_model.parse_obj(report) for report in self._unique(news_list)]

        except Exception as e:
            traceback.print_exc()
            self._logger.error(f"Error: {e}")
            return []
        
        
    async def count(self, query: dict) -> int:
        try:
            # TODO: remove duplicate entries
            news_count = await self._db_model.count(query)

            return news_count

        except Exception as e:
            traceback.print_exc()
            self._logger.error(f"Error: {e}")
            return 0

    async def add_one(self, data: BaseModel) -> BaseModel:
        return NotImplemented

    async def add_many(self, data_list: List[BaseModel]) -> List[BaseModel]:
        return NotImplemented

    async def get_one(self, id: str) -> BaseModel:
        return NotImplemented

    async def update_one(self, id: str, update_data: BaseModel) -> None:
        pass

    async def update_many(self, query: dict, data_list: List[BaseModel]) -> None:
        pass

    async def delete_one(self, id: str) -> None:
        pass

    async def delete_many(self, query: dict) -> None:
        pass


if __name__ == "__main__":
    import asyncio

    from devtools import debug

    from ..db.client import create_client

    async def main():
        db_client = create_client(host='localhost',
                                  username='admin',
                                  password='root',
                                  port=27017,
                                  db_name='test')
        NewsDBModel.db = db_client['test']
        news_service = NewsService(data_model=News, db_model=NewsDBModel)

        news_list = await news_service.get_many({'themeId': 0}, page_size=30, page_number=0)

        debug(news_list)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
