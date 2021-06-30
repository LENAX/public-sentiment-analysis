from typing import List, Any, Coroutine
from .base_services import BaseAsyncCRUDService
from ..models.db_models import News
from ..models.data_models import NewsData
from ..models.request_models import QueryArgs
from datetime import datetime
from asyncio import Lock

import logging
from logging import Logger, getLogger

LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y/%m/%d %H:%M:%S %p"
logging.basicConfig(level=logging.DEBUG,
                    format=LOG_FORMAT, datefmt=DATE_FORMAT)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class NewsService(BaseAsyncCRUDService):
    """ Provides News Data Access
    """

    def __init__(self,
                 news_db_model: News = News,
                 news_data_model: NewsData = NewsData,
                 logger: Logger = getLogger(f"{__name__}.NewsService")):
        self._news_db_model = news_db_model
        self._news_data_model = news_data_model
        self._logger = logger

    async def add_one(self, data: NewsData) -> NewsData:  # type: ignore[override]
        """ Add a new news record

        Args:
            data (NewsData): news data model

        Returns:
            NewsData: the newly added news record
        """
        try:
            new_news_record = self._news_db_model.parse_obj(data)
            await new_news_record.save()
            return self._news_data_model.from_db_model(new_news_record)
        except Exception as e:
            self._logger.error(
                "Fail to create a new news record", exc_info=True)
            raise e

    # type: ignore[override]
    async def add_many(self, data_list: Coroutine[Any, Any, List[NewsData]]) -> Coroutine[Any, Any, List[NewsData]]:
        try:
            new_news_records = self._news_db_model.parse_many(
                data_list)
            await self._news_db_model.insert_many(new_news_records)
            return data_list
        except Exception as e:
            self._logger.error(
                "Fail to insert new news records", exc_info=True)
            raise e

    async def get_one(self, id: str) -> NewsData:
        try:
            news_record = await self._news_db_model.get_one({"news_id": id})
            return self._news_data_model.from_db_model(news_record)
        except Exception as e:
            self._logger.error(
                f"Fail to retrieve news record of id {id}", exc_info=True)
            raise e

    # type: ignore[override]
    async def get_many(self, query: dict) -> Coroutine[Any, Any, List[NewsData]]:
        try:
            news_record = await self._news_db_model.get(query)
            return [self._news_data_model.from_db_model(record)
                    for record in news_record]
        except Exception as e:
            self._logger.error(
                f"Fail to retrieve news records given query {query}", exc_info=True)
            raise e

    async def update_one(self, id: str, update_data: NewsData) -> None:  # type: ignore[override]
        try:
            await self._news_db_model.update_one(
                {"news_id": id}, update_data.dict(exclude_unset=True))
        except Exception as e:
            self._logger.error(
                f"Fail to update news record of id {id}", exc_info=True)
            raise e

    
    async def update_many(self, query: dict, data_list: List[NewsData]) -> None: # type: ignore[override]
        pass

    async def delete_one(self, id: str) -> None:
        try:
            await self._news_db_model.delete_one({"news_id": id})
        except Exception as e:
            self._logger.error(
                f"Fail to delete news record of id {id}", exc_info=True)
            raise e

    async def delete_many(self, query: dict) -> None:
        try:
            await self._news_db_model.delete_many(query)
        except Exception as e:
            self._logger.error(
                f"Fail to delete news records given query {query}", exc_info=True)
            raise e
