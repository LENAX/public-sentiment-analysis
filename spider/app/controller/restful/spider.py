from fastapi import APIRouter, Depends, HTTPException
from ...models.response_models import Response
from ...models.data_models import (
    COVIDReportData, SpecificationData, Schedule, JobStatus)
from app.models.request_models.request_models import ScrapeRules
from typing import Optional, List
from dependency_injector.wiring import inject, Provide
from ...containers import Application
from ...service import DXYCovidReportSpiderService
from datetime import datetime, time, timedelta
from dateutil import parser

import logging

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(funcName)s |%(message)s",
                    datefmt="%Y-%m-%dT%H:%M:%S%z")
spider_logger = logging.getLogger(__name__)
spider_logger.setLevel(logging.DEBUG)


spider_controller = APIRouter()


@spider_controller.get("/spider/status", tags=["spiders"], response_model=Response)
@inject
async def check_status():
    return Response(message="I am alive", statusCode=200, status="success")


@spider_controller.post("/spider/crawl-task", tags=["spiders"], response_model=Response)
@inject
async def crawl_covid_report(urls: List[str],
                             spider_service: DXYCovidReportSpiderService = Depends(Provide[
                                Application.services.spider_services_container.dxy_covid_spider_service])):
    try:
        await spider_service.crawl(urls, None)
        return Response(message="ok", statusCode=200, status="success")
    except Exception as e:
        spider_logger.error(f"Error: {e}")
        return Response(message="error", statusCode=500, status="failed")
    

@spider_controller.get("/spider/historical-data", tags=["spiders"], response_model=Response)
@inject
async def crawl_covid_report(url: str,
                             start_date: str,
                             end_date: str,
                             spider_service: DXYCovidReportSpiderService = Depends(Provide[
                                 Application.services.spider_services_container.dxy_covid_spider_service])):
    try:
        spider_logger.info(f"crawling historical report from {url}, start_date: {start_date}, end_date: {end_date}")
        await spider_service.load_historical_report(url, start_date=parser.parse(start_date), end_date=parser.parse(end_date))
        return Response(message="ok", statusCode=200, status="success")    
    except Exception as e:
        spider_logger.error(f"Error: {e}")
        return Response(message="error", statusCode=500, status="failed")
