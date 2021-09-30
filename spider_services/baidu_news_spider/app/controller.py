import logging
import traceback
from datetime import datetime, timedelta
from itertools import product
from logging import Logger
from typing import Callable

from dateutil import parser
from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from ...common.models.request_models import (BaiduNewsSpiderArgs, ScrapeRules,
                                             TimeRange)
from ...common.models.response_models import Response
from .container import Application
from .service import BaiduNewsSpiderService
from .utils import load_service_config


def create_logger():
    logging.basicConfig(format="%(asctime)s | %(levelname)s | %(funcName)s | %(message)s",
                        datefmt="%Y-%m-%dT%H:%M:%S")
    spider_logger = logging.getLogger(__name__)
    spider_logger.setLevel(logging.DEBUG)
    return spider_logger


def load_config(config_name):
    return lambda _: load_service_config(config_name)


spider_controller = APIRouter()


@spider_controller.get("/baidu-news-spider/status", tags=["baidu-news-spider"], response_model=Response)
@inject
async def check_status():
    return Response(message="I am alive", statusCode=200, status="success")


@spider_controller.post("/baidu-news-spider/crawl-task", tags=["baidu-news-spider"], response_model=Response)
@inject
async def get_baidu_news(args: BaiduNewsSpiderArgs,
                         background_tasks: BackgroundTasks,
                         spider_service: BaiduNewsSpiderService = Depends(Provide[
                             Application.services.baidu_news_spider_service]),
                         rules: ScrapeRules = Depends(load_config('baidu_news')),
                         product: Callable = product,
                         spider_logger: Logger = Depends(create_logger)):
    try:
        rules.keywords.include = product(args.area_keywords, args.theme_keywords)

        spider_logger.info(f"Start crawling {args.url} with keywords {rules.keywords.include}...")
        background_tasks.add_task(spider_service.crawl, [args.url], rules)
        spider_logger.info(f"Running in background ...")

        return Response(message="ok", statusCode=200, status="success")

    except Exception as e:
        traceback.print_exc()
        spider_logger.error(f"Error: {e}")
        return Response(message=f"error: {e}", statusCode=500, status="failed")
