from fastapi import APIRouter, Depends

from data_services.news.app.services import NewsService
from ..models.response_models import Response
from ..models.data_models import News, MigrationRank
from ..models.db_models import NewsDBModel, MigrationRankDBModel
from typing import Optional, List
from dependency_injector.wiring import inject, Provide
from ..container import Application
from ..services import NewsReportService, MigrationRankReportService
import traceback
import logging
from datetime import datetime, timedelta
from logging import Logger


def create_logger():
    logging.basicConfig(format="%(asctime)s | %(levelname)s | %(funcName)s |%(message)s",
                        datefmt="%Y-%m-%dT%H:%M:%S%z")
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    return logger


def get_past_n_days(n_days=0):
    return (datetime.now() - timedelta(days=n_days)).strftime("%Y%m%d")


news_controller = APIRouter()


@news_controller.get('/media-monitor/news', tags=["news"], response_model=Response)
@inject
async def get_migration_index(appId: str, themeId: int,
                              startDate: str = get_past_n_days(30),
                              endDate: str = get_past_n_days(0),
                              pageSize: int = 30, pageNumber: int = 0,
                              news_service: NewsService = Depends(Provide[
                                  Application.services.news_service]),
                              logger: Logger = Depends(create_logger)):
    try:
        # could be refactored to a query builder method
        required_args = {'date': {'$gte': startDate, '$lte': endDate},
                         'theme_id': themeId}
        query = {**required_args}
        logger.info(f"query: {query}")
        news_list = await news_service.get_many(query, page_size=pageSize, page_number=pageNumber)
        logger.info(f"news_list: {news_list}")
        return Response[List[News]](data=news_list, message='ok', statusCode=200, status='success')
    except Exception as e:
        traceback.print_exc()
        logger.error(f"{e}")
        return Response(data=[], message=f"{e}", statusCode=500, status="failed")

