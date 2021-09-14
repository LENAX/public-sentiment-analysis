from fastapi import APIRouter, Depends
from ..models.response_models import Response
from ..models.data_models import CMAWeatherReport, CMADailyWeather
from ..models.db_models import CMAWeatherReportDBModel
from typing import Optional, List
from dependency_injector.wiring import inject, Provide
from ..container import Application
from ..services import CMAWeatherReportService
import traceback
import logging
from datetime import datetime
from logging import Logger


def create_logger():
    logging.basicConfig(format="%(asctime)s | %(levelname)s | %(funcName)s |%(message)s",
                        datefmt="%Y-%m-%dT%H:%M:%S%z")
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    return logger

def get_today_date():
    return datetime.now().strftime("%Y-%m-%d")

cma_weather_controller = APIRouter()


@cma_weather_controller.get('/weather/daily', tags=["cma_daily_weather"], response_model=Response[CMADailyWeather])
@inject
async def get_daily_weather(province: str, city: Optional[str],
                            weather_report_service: CMAWeatherReportService = Depends(Provide[
                                Application.services.cma_weather_report_service]),
                            today_date: str = Depends(get_today_date),
                            logger: Logger = Depends(create_logger)):
    try:
        required_args = {'province': province, 'create_dt': today_date}
        optional_args = {'city': city}
        query = {**required_args,
                 **{key: optional_args[key]
                    for key in optional_args if optional_args[key] is not None}}
        daily_weather_reports = await weather_report_service.get_many(query)
        return Response[CMADailyWeather](data=daily_weather_reports, message='ok', statusCode=200, status='success')
    except Exception as e:
        traceback.print_exc()
        logger.error(f"{e}")
        return Response(message=f"{e}", statusCode=500, status="failed"), 500
