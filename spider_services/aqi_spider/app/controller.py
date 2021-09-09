from fastapi import BackgroundTasks, APIRouter, Depends, HTTPException
from ...common.models.response_models import Response
from ...common.models.request_models import ScrapeRules
from typing import Optional, List
from dependency_injector.wiring import inject, Provide
from .container import Application
from .service import AQISpiderService
from datetime import datetime, time, timedelta
from dateutil import parser
from .utils import load_service_config

import logging
from logging import Logger


def create_logger():
    logging.basicConfig(format="%(asctime)s | %(levelname)s | %(funcName)s |%(message)s",
                        datefmt="%Y-%m-%dT%H:%M:%S%z")
    aqi_spider_logger = logging.getLogger(__name__)
    aqi_spider_logger.setLevel(logging.DEBUG)
    return aqi_spider_logger


def load_aqi_config():
    return load_service_config('aqi_config')

aqi_spider_controller = APIRouter()


@aqi_spider_controller.get("/aqi-spider/status", tags=["aqi-spider"], response_model=Response)
@inject
async def check_status():
    return Response(message="I am alive", statusCode=200, status="success")


@aqi_spider_controller.post("/aqi-spider/crawl-task", tags=["aqi-spider"], response_model=Response)
@inject
async def crawl_aqi_report(urls: List[str],
                           background_tasks: BackgroundTasks,
                           rules: ScrapeRules = Depends(load_aqi_config),
                           spider_service: AQISpiderService = Depends(Provide[
                                Application.services.aqi_spider_service]),
                           spider_logger: Logger = Depends(create_logger)):
    try:
        if len(urls) == 0:
            spider_logger.error(f"No url is specified.")
            return Response(message="url should be specified", statusCode=400, status="failed")
        
        spider_logger.info(f"Start crawling {urls} ...")
        spider_logger.info(f"spider service: {spider_service}")
        background_tasks.add_task(spider_service.crawl, urls, rules)
        spider_logger.info(f"Running in background ...")
        return Response(message="ok", statusCode=200, status="success")
    except Exception as e:
        spider_logger.error(f"Error: {e}")
        return Response(message="error", statusCode=500, status="failed")
