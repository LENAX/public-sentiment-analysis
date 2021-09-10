from fastapi import BackgroundTasks, APIRouter, Depends, HTTPException
from ...common.models.response_models import Response
from ...common.models.request_models import ScrapeRules, AQISpiderArgs, TimeRange
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
    return {"history": load_service_config('aqi_config'),
            "update": load_service_config('aqi_daily')}

aqi_spider_controller = APIRouter()


@aqi_spider_controller.get("/aqi-spider/status", tags=["aqi-spider"], response_model=Response)
@inject
async def check_status():
    return Response(message="I am alive", statusCode=200, status="success")


@aqi_spider_controller.post("/aqi-spider/crawl-task", tags=["aqi-spider"], response_model=Response)
@inject
async def crawl_aqi_report(args: AQISpiderArgs,
                           background_tasks: BackgroundTasks,
                           config: ScrapeRules = Depends(load_aqi_config),
                           spider_service: AQISpiderService = Depends(Provide[
                                Application.services.aqi_spider_service]),
                           spider_logger: Logger = Depends(create_logger)):
    try:
        if len(args.url) == 0:
            spider_logger.error(f"No url is specified.")
            return Response(message="url should be specified", statusCode=400, status="failed")
        
        rules = config.get(args.mode, 'update')
        start_date = parser.parse(args.start_date) if type(args.start_date) is str else rules.time_range.start_date
        end_date = parser.parse(args.end_date) if type(args.end_date) is str  else rules.time_range.end_date
        rules.time_range = TimeRange(start_date=start_date, end_date=end_date)

        spider_logger.info(f"Start crawling {args.url} between {start_date} and {end_date}...")
        background_tasks.add_task(spider_service.crawl, [args.url], rules)
        spider_logger.info(f"Running in background ...")
        return Response(message="ok", statusCode=200, status="success")
    except Exception as e:
        spider_logger.error(f"Error: {e}")
        return Response(message="error", statusCode=500, status="failed")
