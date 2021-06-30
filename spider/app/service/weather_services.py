from typing import List, Any, Callable, Union, TypeVar, Sequence
from .base_services import BaseAsyncCRUDService
from ..models.db_models import Weather
from ..models.data_models import WeatherData
from ..models.request_models import QueryArgs
from datetime import datetime
from asyncio import Lock

import logging
from logging import Logger, getLogger

LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%m/%d/%Y %H:%M:%S %p"
logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT, datefmt=DATE_FORMAT)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

WeatherClass = TypeVar("WeatherClass")
WeatherDataClass = TypeVar("WeatherDataClass")

class WeatherService(BaseAsyncCRUDService):
    """ Provides Weather Data Access
    """

    def __init__(self,  
                 weather_db_model: WeatherClass = Weather,
                 weather_data_model: WeatherDataClass = WeatherData,
                 logger: Logger = getLogger(f"{__name__}.WeatherService")):
        self._weather_db_model = weather_db_model
        self._weather_data_model = weather_data_model
        self._logger = logger

    async def add_one(self, data: WeatherData) -> WeatherData:   # type: ignore[override]
        """ Add a new weather record

        Args:
            data (WeatherData): weather data model

        Returns:
            WeatherData: the newly added weather record
        """
        try:
            new_weather_record = self._weather_db_model.parse_obj(data)
            await new_weather_record.save()
            return self._weather_data_model.from_db_model(new_weather_record)
        except Exception as e:
            self._logger.error("Fail to create a new weather record", exc_info=True)
            raise e

    async def add_many(self, data_list: List[WeatherData]) -> List[WeatherData]:  # type: ignore[override]
        try:
            new_weather_records = self._weather_db_model.parse_many(data_list)
            await self._weather_db_model.insert_many(new_weather_records)
            return data_list
        except Exception as e:
            self._logger.error(
                "Fail to insert new weather records", exc_info=True)
            raise e
    
    async def get_one(self, id: str) -> WeatherData:
        try:
            weather_record = await self._weather_db_model.get_one({"weather_id": id})
            self._logger.info(f"Retrieved record: {weather_record}")
            return self._weather_data_model.from_db_model(weather_record)
        except Exception as e:
            self._logger.error(
                f"Fail to retrieve weather record of id {id}", exc_info=True)
            raise e

    async def get_many(self, query: dict) -> List[WeatherData]: # type: ignore[override]
        try:
            weather_record = await self._weather_db_model.get(query)
            return [self._weather_data_model.from_db_model(record)
                    for record in weather_record]
        except Exception as e:
            self._logger.error(
                f"Fail to retrieve weather records given query {query}", exc_info=True)
            raise e
    
    async def update_one(self, id: str, update_data: WeatherData) -> None:   # type: ignore[override]
        try:
            await self._weather_db_model.update_one(
                {"weather_id": id}, update_data.dict(exclude_unset=True))
        except Exception as e:
            self._logger.error(
                f"Fail to update weather record of id {id}", exc_info=True)
            raise e
        
    async def update_many(self, query: dict, data_list: List[WeatherData]) -> None:  # type: ignore[override]
        pass

    async def delete_one(self, id: str) -> None:
        try:
            await self._weather_db_model.delete_one({"weather_id": id})
        except Exception as e:
            self._logger.error(
                f"Fail to delete weather record of id {id}", exc_info=True)
            raise e

    async def delete_many(self, query: dict) -> None:
        try:
            await self._weather_db_model.delete_many(query)
        except Exception as e:
            self._logger.error(
                f"Fail to delete weather records given query {query}", exc_info=True)
            raise e
