from typing import List, Any, Coroutine
from .base_services import BaseAsyncCRUDService
from ..models.db_models import Specification
from ..models.data_models import SpecificationData
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


class SpecificationService(BaseAsyncCRUDService):
    """ Provides Specification Data Access
    """

    def __init__(self,
                 job_specification_db_model: Specification = Specification,
                 job_specification_data_model: SpecificationData = SpecificationData,
                 logger: Logger = getLogger(f"{__name__}.SpecificationService")):
        self._job_specification_db_model = job_specification_db_model
        self._job_specification_data_model = job_specification_data_model
        self._logger = logger

    # type: ignore[override]
    async def add_one(self, data: SpecificationData) -> SpecificationData:
        """ Add a new job_specification record

        Args:
            data (SpecificationData): job_specification data model

        Returns:
            SpecificationData: the newly added job_specification record
        """
        try:
            new_job_specification_record = self._job_specification_db_model.parse_obj(data)
            await new_job_specification_record.save()
            return self._job_specification_data_model.from_db_model(new_job_specification_record)
        except Exception as e:
            self._logger.error(
                "Fail to create a new job_specification record", exc_info=True)
            raise e

    # type: ignore[override]
    async def add_many(self, data_list: Coroutine[Any, Any, List[SpecificationData]]) -> Coroutine[Any, Any, List[SpecificationData]]:
        try:
            new_job_specification_records = self._job_specification_db_model.parse_many(
                data_list)
            await self._job_specification_db_model.insert_many(new_job_specification_records)
            return data_list
        except Exception as e:
            self._logger.error(
                "Fail to insert new job_specification records", exc_info=True)
            raise e

    async def get_one(self, id: str) -> SpecificationData:
        try:
            job_specification_record = await self._job_specification_db_model.get_one({"job_specification_id": id})
            return self._job_specification_data_model.from_db_model(job_specification_record)
        except Exception as e:
            self._logger.error(
                f"Fail to retrieve job_specification record of id {id}", exc_info=True)
            raise e

    # type: ignore[override]
    async def get_many(self, query: dict) -> Coroutine[Any, Any, List[SpecificationData]]:
        try:
            job_specification_record = await self._job_specification_db_model.get(query)
            return [self._job_specification_data_model.from_db_model(record)
                    for record in job_specification_record]
        except Exception as e:
            self._logger.error(
                f"Fail to retrieve job_specification records given query {query}", exc_info=True)
            raise e

    async def update_one(self, id: str, update_data: SpecificationData) -> None:  # type: ignore[override]
        try:
            await self._job_specification_db_model.update_one(
                {"job_specification_id": id}, update_data.dict(exclude_unset=True))
        except Exception as e:
            self._logger.error(
                f"Fail to update job_specification record of id {id}", exc_info=True)
            raise e
        
        
    async def update_many(self, query: dict, data_list: List[SpecificationData]) -> None: # type: ignore[override]
        pass

    async def delete_one(self, id: str) -> None:
        try:
            await self._job_specification_db_model.delete_one({"job_specification_id": id})
        except Exception as e:
            self._logger.error(
                f"Fail to delete job_specification record of id {id}", exc_info=True)
            raise e

    async def delete_many(self, query: dict) -> None:
        try:
            await self._job_specification_db_model.delete_many(query)
        except Exception as e:
            self._logger.error(
                f"Fail to delete job_specification records given query {query}", exc_info=True)
            raise e
