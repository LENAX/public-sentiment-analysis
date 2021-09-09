from typing import List, Any, Coroutine
from .base_services import BaseAsyncCRUDService
from ..models.db_models import CMAWeatherReportDBModel, AirQualityDBModel
from ..models.data_models import WeatherAQI
import numpy as np
import traceback
import logging
from logging import Logger, getLogger

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(funcName)s |%(message)s",
                    datefmt="%Y-%m-%dT%H:%M:%S%z")
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class WeatherAQIService(BaseAsyncCRUDService):
    """ Provides Weather and AQI Data Access
    """

    def __init__(self,
                 cma_weather_report_db_model: CMAWeatherReportDBModel,
                 aqi_db_model: AirQualityDBModel,     
                 weather_aqi_data_model: WeatherAQI,
                 logger: Logger = logger):
        self._cma_weather_report_db_model = cma_weather_report_db_model
        self._aqi_db_model = aqi_db_model
        self._weather_aqi_data_model = weather_aqi_data_model
        self._logger = logger


    async def get_many(self, query: dict) -> List[WeatherAQI]:
        try:
            # query should include province, city, start date and end date
            cma_weather_reports = await self._cma_weather_report_db_model.get_many(query)
            aqi_reports = await self._aqi_db_model.get_many(query)
            
            if len(cma_weather_reports) == 0 or len(aqi_reports) == 0:
                return []
            
            
            
        except Exception as e:
            traceback.print_exc()
            self._logger.error(f"Error: {e}")

