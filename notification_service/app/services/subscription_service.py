from .base_crud_service import BaseAsyncCRUDService
from ..models.data_models import Subscription as SubscriptionData
from ..models.db_models import SubscriptionDBModel
import traceback
from typing import List
import logging
from logging import Logger

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(funcName)s | %(message)s",
                    datefmt="%Y-%m-%dT%H:%M:%S%z")
subscription_service_logger = logging.getLogger(__name__)
subscription_service_logger.setLevel(logging.DEBUG)


class SubscriptionService(BaseAsyncCRUDService):
    
    def __init__(self,
                 subscription_data_model: SubscriptionData,
                 subscription_db_model: SubscriptionDBModel,
                 logger: Logger = subscription_service_logger):
        self._data_model = subscription_data_model
        self._db_model = subscription_db_model
        self._logger = logger

    async def add_many(self, data_list: List[SubscriptionData]) -> None:
        try:
            await self._db_model.insert_many(
                [self._db_model.parse_obj(data) for data in data_list])
        except Exception as e:
            traceback.print_exc()
            self._logger.error(f"{e}")
            raise e
    
    async def get_many(self, query: dict) -> List[SubscriptionData]:
        try:
            query_results = await self._db_model.get_many(query)
            return [self._data_model.parse_obj(result) for result in query_results]
        except Exception as e:
            traceback.print_exc()
            self._logger.error(f"{e}")
            raise e
    
    async def update_one(self, query: dict, data: SubscriptionData) -> None:
        try:
            await self._db_model.update_one(query, data.dict())
        except Exception as e:
            traceback.print_exc()
            self._logger.error(f"{e}")
            raise e
    
    async def update_many(self, query: dict, update_data: SubscriptionData) -> None:
        try:
            await self._db_model.update_many(query, update_data.dict())
        except Exception as e:
            traceback.print_exc()
            self._logger.error(f"{e}")
            raise e
    
    async def delete_many(self, query: dict) -> None:
        try:
            await self._db_model.delete_many(query)
        except Exception as e:
            traceback.print_exc()
            self._logger.error(f"{e}")
            raise e
