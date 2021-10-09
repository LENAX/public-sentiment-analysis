from fastapi import APIRouter, Depends

from ..models.response_models import Response
from ..models.data_models import AirQuality
from ..models.db_models import AirQualityDBModel
from typing import Optional, List
from dependency_injector.wiring import inject, Provide
from ..container import Application
from ..services import AQIReportService, AQIHistoryService
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

aqi_controller = APIRouter()


@aqi_controller.get('/aqi/now', tags=["aqi_report"], response_model=Response[List[AirQuality]])
@inject
async def get_aqi_report(province: str = '湖北', city: Optional[str] = None,
                         aqi_report_service: AQIReportService = Depends(Provide[
                             Application.services.aqi_report_service]),
                         today_date: str = Depends(get_today_date),
                         logger: Logger = Depends(create_logger)):
    try:
        required_args = {'province': province, 'date': {'$gte': today_date}}
        optional_args = {'city': city}
        query = {**required_args,
                 **{key: optional_args[key]
                    for key in optional_args if optional_args[key] is not None}}
        logger.info(f"query: {query}")
        aqi_reports = await aqi_report_service.get_many(query)
        return Response[List[AirQuality]](data=aqi_reports, message='ok', statusCode=200, status='success')
    except Exception as e:
        traceback.print_exc()
        logger.error(f"{e}")
        return Response(message=f"{e}", statusCode=500, status="failed")


@aqi_controller.get('/aqi/history', tags=["aqi_report"], response_model=Response[List[AirQuality]])
@inject
async def get_aqi_history(province: str = '湖北', city: Optional[str] = None,
                          pageNumber: Optional[int] = 0, pageSize: Optional[int] = 30,
                          startDate: Optional[str] = '2021-10-01', endDate: Optional[str] = get_today_date(),
                          aqi_history_service: AQIHistoryService = Depends(Provide[
                              Application.services.aqi_history_service]),
                          logger: Logger = Depends(create_logger)):
    try:
        required_args = {'province': province, 'date': {'$gte': startDate, '$lte': endDate}}
        optional_args = {'city': city}
        query = {**required_args,
                 **{key: optional_args[key]
                    for key in optional_args if optional_args[key] is not None}}
        logger.info(f"query: {query}")
        aqi_reports = await aqi_history_service.get_many(query, page_size=pageSize, page_number=pageNumber)
        return Response[List[AirQuality]](data=aqi_reports, message='ok', statusCode=200, status='success')
    except Exception as e:
        traceback.print_exc()
        logger.error(f"{e}")
        return Response(message=f"{e}", statusCode=500, status="failed")
