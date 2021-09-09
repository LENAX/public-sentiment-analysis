from typing import List, Any, Coroutine
from .base_services import BaseAsyncCRUDService
from ..models.db_models import CMAWeatherReportDBModel, AirQualityDBModel
from ..models.data_models import COVIDReportData
import numpy as np
import logging
from logging import Logger, getLogger

LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y/%m/%d %H:%M:%S %p"
logging.basicConfig(level=logging.DEBUG,
                    format=LOG_FORMAT, datefmt=DATE_FORMAT)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class WeatherAQIService(BaseAsyncCRUDService):
    """ Provides Weather and AQI Data Access
    """

    def __init__(self,
                 cma_weather_report_db_model: CMAWeatherReportDBModel,
                 aqi_db_model: AirQualityDBModel,     
                 covid_report_data_model: COVIDReportData = COVIDReportData,
                 logger: Logger = getLogger(f"{__name__}.COVIDReportService")):
        self._covid_report_db_model = covid_report_db_model
        self._covid_report_data_model = covid_report_data_model
        self._logger = logger

