import logging
import traceback
from datetime import datetime, timedelta
from itertools import product
from logging import Logger
from typing import Callable, List

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


def load_config():
    return load_service_config('baidu_news')


def build_keyword(keyword_list: List[str]) -> str:
    return f"%7B{'%2C'.join(keyword_list)}%7B"


def build_pattern(area_keywords: List[str], other_keywords: List[str]) -> str:
    if len(area_keywords) == 0 or len(other_keywords) == 0:
        return r""
    
    return r"(?=.*({}))(?=.*({}))".format("|".join(area_keywords), "|".join(other_keywords))

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
                         rules: ScrapeRules = Depends(load_config),
                         spider_logger: Logger = Depends(create_logger)):
    try:
        if len(args.area_keywords) == 0 and len(args.theme_keywords) == 0 and len(args.epidemic_keywords) == 0:
            return Response(message="area_keywords, theme_keywords and epidemic_keywords are required",
                            status="failed",
                            statusCode=412)
        
        theme_keywords = [kw.keyword for kw in args.theme_keywords]
        keyword_combination = f"{build_keyword(args.area_keywords)}+" +\
                                f"{build_keyword(theme_keywords)}+" +\
                                f"{build_keyword(args.epidemic_keywords)}"
        article_pattern = build_pattern(args.area_keywords, theme_keywords+args.epidemic_keywords)
            
        # "%2B" is url encoded form of + sign
        rules.keywords.include = [keyword_combination]
        rules.url_patterns = [article_pattern]
        
        rules.theme_id = args.theme_id
        rules.time_range.past_days = args.past_days

        spider_logger.info(f"Start crawling {args.url} with keywords {rules.keywords.include}...")
        background_tasks.add_task(spider_service.crawl, [args.url], rules)
        spider_logger.info(f"Running in background ...")

        return Response(message="ok", statusCode=200, status="success")

    except Exception as e:
        traceback.print_exc()
        spider_logger.error(f"Error: {e}")
        return Response(message=f"error: {e}", statusCode=500, status="failed")
