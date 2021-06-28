from typing import List, Any, Coroutine
from .base_services import BaseAsyncCRUDService
from ..models.db_models import AirQuality
from ..models.data_models import AirQualityData
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


class AirQualityService(BaseAsyncCRUDService):
    """ Provides AirQuality Data Access
    """

    def __init__(self,
                 air_quality_db_model: AirQuality = AirQuality,
                 air_quality_data_model: AirQualityData = AirQualityData,
                 logger: Logger = getLogger(f"{__name__}.AirQualityService")):
        self._air_quality_db_model = air_quality_db_model
        self._air_quality_data_model = air_quality_data_model
        self._logger = logger

    async def add_one(self, data: AirQualityData) -> AirQualityData:   # type: ignore[override]
        """ Add a new air_quality record

        Args:
            data (AirQualityData): air_quality data model

        Returns:
            AirQualityData: the newly added air_quality record
        """
        try:
            new_air_quality_record = self._air_quality_db_model.parse_obj(data)
            await new_air_quality_record.save()
            return self._air_quality_data_model.from_db_model(new_air_quality_record)
        except Exception as e:
            self._logger.error(
                "Fail to create a new air_quality record", exc_info=True)
            raise e

    
    async def add_many(self, data_list: Coroutine[Any, Any, List[AirQualityData]]) -> Coroutine[Any, Any, List[AirQualityData]]:  # type: ignore[override]
        try:
            new_air_quality_records = self._air_quality_db_model.parse_many(data_list)
            await self._air_quality_db_model.insert_many(new_air_quality_records)
            return data_list
        except Exception as e:
            self._logger.error(
                "Fail to insert new air_quality records", exc_info=True)
            raise e

    async def get_one(self, id: str) -> AirQualityData:
        try:
            air_quality_record = await self._air_quality_db_model.get_one({"air_quality_id": id})
            return self._air_quality_data_model.from_db_model(air_quality_record)
        except Exception as e:
            self._logger.error(
                f"Fail to retrieve air_quality record of id {id}", exc_info=True)
            raise e

    async def get_many(self, query: QueryArgs) -> Coroutine[Any, Any, List[AirQualityData]]:   # type: ignore[override]
        try:
            air_quality_record = await self._air_quality_db_model.get(query.dict(exclude_unset=True))
            return [self._air_quality_data_model.from_db_model(record)
                    for record in air_quality_record]
        except Exception as e:
            self._logger.error(
                f"Fail to retrieve air_quality records given query {query}", exc_info=True)
            raise e

    async def update_one(self, id: str, update_data: AirQualityData) -> None:   # type: ignore[override]
        try:
            await self._air_quality_db_model.update_one(
                {"air_quality_id": id}, update_data.dict(exclude_unset=True))
        except Exception as e:
            self._logger.error(
                f"Fail to update air_quality record of id {id}", exc_info=True)
            raise e

    async def delete_one(self, id: str) -> None:
        try:
            await self._air_quality_db_model.delete_one({"air_quality_id": id})
        except Exception as e:
            self._logger.error(
                f"Fail to delete air_quality record of id {id}", exc_info=True)
            raise e

    async def delete_many(self, query: QueryArgs) -> None:
        try:
            await self._air_quality_db_model.delete_many(query.dict(exclude_unset=True))
        except Exception as e:
            self._logger.error(
                f"Fail to delete air_quality records given query {query}", exc_info=True)
            raise e
