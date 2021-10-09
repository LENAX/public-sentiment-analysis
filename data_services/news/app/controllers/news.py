from fastapi import APIRouter, Depends
from data_services.news.app.models.response_models.news import NewsResponse

from data_services.news.app.services import NewsService
from ..models.response_models import Response
from ..models.data_models import News
from typing import List
from dependency_injector.wiring import inject, Provide
from ..container import Application
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
    return (datetime.now() - timedelta(days=n_days)).strftime("%Y-%m-%d")


news_controller = APIRouter()


@news_controller.get('/media-monitor/news', tags=["news"], response_model=Response)
@inject
async def get_news(appId: str, themeId: int,
                    startDate: str = get_past_n_days(30),
                    endDate: str = get_past_n_days(0),
                    pageSize: int = 30, pageNumber: int = 0,
                    news_service: NewsService = Depends(Provide[
                        Application.services.news_service]),
                    logger: Logger = Depends(create_logger)):
    try:
        # could be refactored to a query builder method
        required_args = {'date': {'$gte': startDate, '$lte': endDate},
                         'themeId': themeId}
        query = {**required_args}
        logger.info(f"query: {query}")
        news_list = await news_service.get_many(query, page_size=pageSize, page_number=pageNumber)
        logger.info(f"news_list: {news_list}")
        
        if len(news_list) > 0:
            news_response = NewsResponse(
                total=len(news_list),
                themeId=themeId,
                createDt=news_list[-1].create_dt,
                articles=news_list
            )
            return Response[NewsResponse](data=news_response, message='ok', statusCode=200, status='success')
        else:
            return Response(data=None, message=f"No news available", statusCode=500, status="failed")
    
    except Exception as e:
        traceback.print_exc()
        logger.error(f"{e}")
        return Response(data=None, message=f"{e}", statusCode=500, status="failed")

