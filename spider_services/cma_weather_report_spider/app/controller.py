from fastapi import BackgroundTasks, APIRouter, Depends, HTTPException
from ...common.models.response_models import Response
from ...common.models.request_models import SpiderArgs
from dependency_injector.wiring import inject, Provide
from .container import Application
from .service import WeatherForecastSpiderService
import traceback

import logging

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(funcName)s |%(message)s",
                    datefmt="%Y-%m-%dT%H:%M:%S%z")
spider_logger = logging.getLogger(__name__)
spider_logger.setLevel(logging.DEBUG)


spider_controller = APIRouter()


@spider_controller.get("/weather-forecast-spider/status", tags=["weather-forecast-spider"], response_model=Response)
@inject
async def check_status():
    return Response[str](data="I am alive", statusCode=200, status="success")


@spider_controller.post("/weather-forecast-spider/crawl-task", tags=["weather-forecast-spider"], response_model=Response)
@inject
async def get_aqi_report(args: SpiderArgs,
                         background_tasks: BackgroundTasks,
                         spider_service: WeatherForecastSpiderService = Depends(Provide[
                            Application.services.spider_services_container.weather_forecast_spider_service])):
    try:
        background_tasks.add_task(spider_service.crawl, args.urls, args.rules)
        return Response(message="Task created successfully.", statusCode=200, status="success")
    except Exception as e:
        traceback.print_exc()
        spider_logger.error(f"Error: {e}")
        return Response(message=f"error: {e}", statusCode=500, status="failed")
