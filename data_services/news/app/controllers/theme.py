from fastapi import APIRouter, Depends
from ..models.response_models import Response
from ..models.data_models import Theme
from typing import Optional, List
from dependency_injector.wiring import inject, Provide
from ..container import Application
from ..services import ThemeService
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

theme_controller = APIRouter()


@theme_controller.get('/media-monitor/theme', tags=["theme"], response_model=Response)
@inject
async def new_theme(pageSize: int = 0, pageNumber: int = 0,
                    theme_service: ThemeService = Depends(Provide[
                        Application.services.theme_service]),
                    logger: Logger = Depends(create_logger)):
    try:
        theme_list = await theme_service.get_many({}, page_size=pageSize, page_number=pageNumber)
        logger.info(f"theme list: {theme_list}")
        return Response[List[Theme]](data=theme_list, message='ok', statusCode=200, status='success')
    except Exception as e:
        traceback.print_exc()
        logger.error(f"{e}")
        return Response(message=f"{e}", statusCode=500, status="failed")


@theme_controller.post('/media-monitor/theme', tags=["theme"], response_model=Response)
@inject
async def new_theme(theme: Theme,
                    theme_service: ThemeService = Depends(Provide[
                        Application.services.theme_service]),
                    logger: Logger = Depends(create_logger)):
    try:
        await theme_service.add_one(theme)
        logger.info(f"added theme: {theme}")
        return Response(message='ok', statusCode=200, status='success')
    except Exception as e:
        traceback.print_exc()
        logger.error(f"{e}")
        return Response(message=f"{e}", statusCode=500, status="failed")


@theme_controller.put('/media-monitor/theme', tags=["theme"], response_model=Response)
@inject
async def update_theme(theme: Theme,
                       theme_service: ThemeService = Depends(Provide[
                           Application.services.theme_service]),
                       logger: Logger = Depends(create_logger)):
    try:
        await theme_service.update_one(theme.themeId, theme)
        logger.info(f"added theme: {theme}")
        return Response(message='ok', statusCode=200, status='success')
    except Exception as e:
        traceback.print_exc()
        logger.error(f"{e}")
        return Response(message=f"{e}", statusCode=500, status="failed")
    

@theme_controller.delete('/media-monitor/theme', tags=["theme"], response_model=Response)
@inject
async def delete_theme(appId: str, themeId: int,
                       theme_service: ThemeService = Depends(Provide[
                            Application.services.theme_service]),
                       logger: Logger = Depends(create_logger)):
    try:
        await theme_service.delete_one(themeId)
        logger.info(f"deleted theme: {themeId}")
        return Response(message='ok', statusCode=200, status='success')
    except Exception as e:
        traceback.print_exc()
        logger.error(f"{e}")
        return Response(message=f"{e}", statusCode=500, status="failed")
