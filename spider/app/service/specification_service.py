from typing import List, Any, Coroutine, TypeVar
from .base_services import BaseAsyncCRUDService
from ..models.db_models import Specification
from ..models.data_models import SpecificationData
from ..models.request_models import QueryArgs
from datetime import datetime
from asyncio import Lock

import logging
from logging import Logger, getLogger

from devtools import debug

LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y/%m/%d %H:%M:%S %p"
logging.basicConfig(level=logging.DEBUG,
                    format=LOG_FORMAT, datefmt=DATE_FORMAT)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

Spec_Model_Type = TypeVar("Spec_Model_Type", bound=Specification)
Spec_Data_Type = TypeVar("Spec_Data_Type", bound=SpecificationData)


class SpecificationService(BaseAsyncCRUDService):
    """ Provides Specification Data Access
    """

    def __init__(self,
                 specification_db_model: Spec_Model_Type = Specification,
                 specification_data_model: Spec_Data_Type = SpecificationData,
                 logger: Logger = getLogger(f"{__name__}.SpecificationService")):
        self._specification_db_model = specification_db_model
        self._specification_data_model = specification_data_model
        self._logger = logger

    # type: ignore[override]
    async def add_one(self, data: SpecificationData) -> SpecificationData:
        """ Add a new specification record

        Args:
            data (SpecificationData): specification data model

        Returns:
            SpecificationData: the newly added specification record
        """
        try:
            new_specification_record = self._specification_db_model.parse_obj(data)
            await new_specification_record.save()
            return self._specification_data_model.from_db_model(new_specification_record)
        except Exception as e:
            self._logger.error(
                "Fail to create a new specification record", exc_info=True)
            raise e

    # type: ignore[override]
    async def add_many(self, data_list: List[SpecificationData]) -> Coroutine[Any, Any, List[SpecificationData]]:
        try:
            new_specification_records = self._specification_db_model.parse_many(
                data_list)
            await self._specification_db_model.insert_many(new_specification_records)
            return data_list
        except Exception as e:
            self._logger.error(
                "Fail to insert new specification records", exc_info=True)
            raise e

    async def get_one(self, id: str) -> SpecificationData:
        if type(id) is not str:
            id = str(id)

        try:
            specification_record = await self._specification_db_model.get_one({"specification_id": id})
            return self._specification_data_model.from_db_model(specification_record)
        except Exception as e:
            self._logger.error(
                f"Fail to retrieve specification record of id {id}", exc_info=True)
            raise e

    # type: ignore[override]
    async def get_many(self, query: dict) -> Coroutine[Any, Any, List[SpecificationData]]:
        try:
            specification_record = await self._specification_db_model.get(query)
            return [self._specification_data_model.from_db_model(record)
                    for record in specification_record]
        except Exception as e:
            self._logger.error(
                f"Fail to retrieve specification records given query {query}", exc_info=True)
            raise e

    async def update_one(self, id: str, update_data: SpecificationData) -> None:  # type: ignore[override]
        if type(id) is not str:
            id = str(id)
        
        try:
            data = update_data.dict(exclude_unset=True)
            data.pop("specification_id")
            await self._specification_db_model.update_one(
                {"specification_id": id}, data)
        except Exception as e:
            self._logger.error(
                f"Fail to update specification record of id {id}", exc_info=True)
            raise e
        
        
    async def update_many(self, query: dict, data_list: List[SpecificationData]) -> None: # type: ignore[override]
        pass

    async def delete_one(self, id: str) -> None:
        if type(id) is not str:
            id = str(id)
        try:
            await self._specification_db_model.delete_one({"specification_id": id})
        except Exception as e:
            self._logger.error(
                f"Fail to delete specification record of id {id}", exc_info=True)
            raise e

    async def delete_many(self, query: dict) -> None:
        try:
            await self._specification_db_model.delete_many(query)
        except Exception as e:
            self._logger.error(
                f"Fail to delete specification records given query {query}", exc_info=True)
            raise e
