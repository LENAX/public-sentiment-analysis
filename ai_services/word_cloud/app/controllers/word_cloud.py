import logging
import traceback
from datetime import datetime, timedelta
from itertools import product
from logging import Logger
from typing import Callable

from dateutil import parser
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from ..models.response_models import Response
from ..container import Application
from ..services.wc_service import WordCloudGenerationService


def create_logger():
    logging.basicConfig(format="%(asctime)s | %(levelname)s | %(funcName)s | %(message)s",
                        datefmt="%Y-%m-%dT%H:%M:%S")
    spider_logger = logging.getLogger(__name__)
    spider_logger.setLevel(logging.DEBUG)
    return spider_logger


wc_controller = APIRouter()


@wc_controller.get("/word-cloud-service/status", tags=["word-cloud"], response_model=Response)
@inject
async def check_status():
    return Response(message="I am alive", statusCode=200, status="success")


@wc_controller.post("/word-cloud", tags=["word-cloud"], response_model=Response)
@inject
async def compute_word_cloud(args: WordCloudArgs,
                             background_tasks: BackgroundTasks,
                             spider_service: BaiduNewsSpiderService = Depends(Provide[
                                Application.services.baidu_news_spider_service]),
                             rules: ScrapeRules = Depends(load_config),
                            spider_logger: Logger = Depends(create_logger)):
    pass
