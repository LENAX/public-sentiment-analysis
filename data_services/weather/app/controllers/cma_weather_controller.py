from fastapi import APIRouter, Depends
from ..models.response_models import Response
from ..models.data_models import CMAWeatherReport, CMADailyWeather
from ..models.db_models import CMAWeatherReportDBModel
from typing import Optional, List
from dependency_injector.wiring import inject, Provide
from ..container import Application
from ..services import CMAWeatherReportService, WeatherHistoryService
import traceback
import logging
from datetime import datetime
from logging import Logger, log


def create_logger():
    logging.basicConfig(format="%(asctime)s | %(levelname)s | %(funcName)s |%(message)s",
                        datefmt="%Y-%m-%dT%H:%M:%S%z")
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    return logger

def get_today_date():
    return datetime.now().strftime("%Y-%m-%d")

cma_weather_controller = APIRouter()


@cma_weather_controller.get('/weather/now', tags=["cma_daily_weather"], response_model=Response)
@inject
async def get_daily_weather(province: str = '湖北', city: Optional[str] = None,
                            weather_report_service: CMAWeatherReportService = Depends(Provide[
                                Application.services.cma_weather_report_service]),
                            today_date: str = Depends(get_today_date),
                            logger: Logger = Depends(create_logger)):
    try:
        required_args = {'location.province': province, 'create_dt': {'$gte': today_date}}
        optional_args = {'city': city}
        query = {**required_args,
                 **{key: optional_args[key]
                    for key in optional_args if optional_args[key] is not None}}
        logger.info(f"query: {query}")
        cma_weather_reports = await weather_report_service.get_many(query)
        return Response[List[CMADailyWeather]](data=cma_weather_reports, message='ok', statusCode=200, status='success')
    except Exception as e:
        traceback.print_exc()
        logger.error(f"{e}")
        return Response(message=f"{e}", statusCode=500, status="failed"), 500


@cma_weather_controller.get('/weather/history', tags=["cma_daily_weather"], response_model=Response)
@inject
async def get_weather_history(province: str = '湖北', city: Optional[str] = None, areaCode: Optional[str] = None,
                              pageNumber: Optional[int] = 0, pageSize: Optional[int] = 30,
                              startDate: Optional[str] = '2021-10-01', endDate: Optional[str] = get_today_date(),
                              weather_history_service: WeatherHistoryService = Depends(Provide[
                                Application.services.weather_history_service]),
                              today_date: str = Depends(get_today_date),
                              logger: Logger = Depends(create_logger)):
    try:
        required_args = {'location.province': province,
                         'create_dt': {'$gte': startDate, '$lte': endDate}}
        optional_args = {'location.city': city, 'location.areaCode': areaCode}
        query = {**required_args,
                 **{key: optional_args[key]
                    for key in optional_args if optional_args[key] is not None}}
        logger.info(f"query: {query}")
        historical_weather_reports = await weather_history_service.get_many(query, page_size=pageSize, page_number=pageNumber)
        return Response[List[CMAWeatherReport]](data=historical_weather_reports, message='ok', statusCode=200, status='success')
    except Exception as e:
        traceback.print_exc()
        logger.error(f"{e}")
        return Response(message=f"{e}", statusCode=500, status="failed"), 500
