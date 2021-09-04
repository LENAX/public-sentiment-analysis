from fastapi import APIRouter, Depends, HTTPException
from ...common.models.response_models import Response
# from ...models.data_models import (
#     COVIDReportData, SpecificationData, Schedule, JobStatus)
# from app.models.request_models.request_models import ScrapeRules
from typing import Optional, List
from dependency_injector.wiring import inject, Provide
from .container import Application
from .service import DXYCovidReportSpiderService
from datetime import datetime, time, timedelta
from dateutil import parser

import logging

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(funcName)s |%(message)s",
                    datefmt="%Y-%m-%dT%H:%M:%S%z")
spider_logger = logging.getLogger(__name__)
spider_logger.setLevel(logging.DEBUG)


spider_controller = APIRouter()


@spider_controller.get("/aqi-spider/status", tags=["aqi-spider"], response_model=Response)
@inject
async def check_status():
    return Response(message="I am alive", statusCode=200, status="success")


@spider_controller.get("/aqi-spider/aqi", tags=["aqi-spider"], response_model=Response)
@inject
async def get_aqi_report(src: str,
                         spider_service: DXYCovidReportSpiderService = Depends(Provide[
                            Application.services.spider_services_container.dxy_covid_spider_service])):
    try:
        await spider_service.crawl(src, None)
        return Response(message="ok", statusCode=200, status="success")
    except Exception as e:
        spider_logger.error(f"Error: {e}")
        return Response(message="error", statusCode=500, status="failed")
