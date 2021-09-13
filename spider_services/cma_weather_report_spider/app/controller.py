from fastapi import BackgroundTasks, APIRouter, Depends, HTTPException
from ...common.models.response_models import Response
from ...common.models.request_models import CMAWeatherSpiderArgs
from dependency_injector.wiring import inject, Provide
from .container import Application
from .service import CMAWeatherReportSpiderService
import traceback

import logging
from logging import Logger

def create_logger():
    logging.basicConfig(format="%(asctime)s | %(levelname)s | %(funcName)s |%(message)s",
                        datefmt="%Y-%m-%dT%H:%M:%S%z")
    spider_logger = logging.getLogger(__name__)
    spider_logger.setLevel(logging.DEBUG)
    return spider_logger


spider_controller = APIRouter()


@spider_controller.get("/cma-weather-spider/status", tags=["weather-forecast-spider"], response_model=Response)
@inject
async def check_status():
    return Response[str](data="I am alive", statusCode=200, status="success")


@spider_controller.post("/cma-weather-spider/crawl-task", tags=["weather-forecast-spider"], response_model=Response)
@inject
async def get_aqi_report(args: CMAWeatherSpiderArgs,
                         background_tasks: BackgroundTasks,
                         spider_service: CMAWeatherReportSpiderService = Depends(Provide[
                            Application.services.weather_forecast_spider_service]),
                         logger: Logger = Depends(create_logger)):
    try:
        logger.info(f"Start crawling weather report in background...")
        background_tasks.add_task(spider_service.crawl, [args.url], None)
        # await spider_service.crawl([args.url], None)
        return Response(message="Task created successfully.", statusCode=200, status="success")
    except Exception as e:
        traceback.print_exc()
        logger.error(f"Error: {e}")
        return Response(message=f"error: {e}", statusCode=500, status="failed")
