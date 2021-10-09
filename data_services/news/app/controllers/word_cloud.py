from fastapi import APIRouter, Depends, BackgroundTasks
from data_services.news.app.models.data_models.word_cloud import NewsWordCloud
from data_services.news.app.models.request_models.word_cloud_arg import WordCloudRequestArgs

from data_services.news.app.models.response_models.word_cloud import WordCloudResponse
from data_services.news.app.services import WordCloudService
from ..models.response_models import Response
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
    return (datetime.now() - timedelta(days=n_days)).strftime("%Y%m%d")


word_cloud_controller = APIRouter()


@word_cloud_controller.post('/media-monitor/wordCloud/compute-task', tags=["media-monitor"], response_model=Response)
@inject
async def compute_word_cloud(args: WordCloudRequestArgs,
                             background_tasks: BackgroundTasks,
                             word_cloud_service: WordCloudService = Depends(Provide[
                                Application.services.word_cloud_service]),
                             logger: Logger = Depends(create_logger)):
    try:
        logger.info("Computing word cloud in the backgrond...")
        background_tasks.add_task(word_cloud_service.compute, args.themeId)
        logger.info("Added task.")
        return Response(message='ok', statusCode=200, status='success')
    except Exception as e:
        traceback.print_exc()
        logger.error(f"{e}")
        return Response(message=f"{e}", statusCode=500, status="failed")


@word_cloud_controller.get('/media-monitor/wordCloud', tags=["media-monitor"], response_model=Response)
@inject
async def get_word_cloud(appId: str, themeId: int,
                         word_cloud_service: WordCloudService = Depends(Provide[
                             Application.services.word_cloud_service]),
                         logger: Logger = Depends(create_logger)):
    try:
        word_cloud = await word_cloud_service.get_one(theme_id=themeId)
        return Response[NewsWordCloud](data=word_cloud, message='ok', statusCode=200, status='success')
    except Exception as e:
        traceback.print_exc()
        logger.error(f"{e}")
        return Response(message=f"{e}", statusCode=500, status="failed")
