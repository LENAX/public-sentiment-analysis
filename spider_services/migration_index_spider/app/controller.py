from fastapi import BackgroundTasks, APIRouter, Depends, HTTPException
from ...common.models.response_models import Response
from ...common.models.request_models import (
    MigrationIndexSpiderArgs, MigrationRankSpiderArgs, ScrapeRules, TimeRange)
from dependency_injector.wiring import inject, Provide
from .container import Application
from .service import MigrationRankSpiderService, MigrationIndexSpiderService
from .utils import load_service_config
from dateutil import parser
from datetime import datetime, timedelta
import traceback

import logging
from logging import Logger

def create_logger():
    logging.basicConfig(format="%(asctime)s | %(levelname)s | %(funcName)s |%(message)s",
                        datefmt="%Y-%m-%dT%H:%M:%S%z")
    spider_logger = logging.getLogger(__name__)
    spider_logger.setLevel(logging.DEBUG)
    return spider_logger


def load_config(spider_name):
    def migration_index_config():
        return load_service_config('migration_index_config')

    def migration_rank_config():
        return load_service_config('migration_rank_config')
    
    config_func = {
        'migration_index': migration_index_config,
        'migration_rank': migration_rank_config
    }
    
    return config_func[spider_name]

def get_yesterday():
    return (datetime.today() - timedelta(days=1))

spider_controller = APIRouter()


@spider_controller.get("/migration-index-spider/status", response_model=Response)
@inject
async def check_status():
    return Response[str](data="I am alive", statusCode=200, status="success")


@spider_controller.post("/migration-index-spider/crawl-task", tags=["migration-index-spider"], response_model=Response)
@inject
async def get_migration_index(args: MigrationIndexSpiderArgs,
                              background_tasks: BackgroundTasks,
                              spider_service: MigrationIndexSpiderService = Depends(Provide[
                                Application.services.migration_index_spider_service]),
                              rules: ScrapeRules = Depends(load_config('migration_index')),
                              spider_logger: Logger = Depends(create_logger)):
    try:
        if len(args.url) == 0:
            spider_logger.error(f"No url is specified.")
            return Response(message="url should be specified", statusCode=400, status="failed")

        rules.mode = args.mode
        rules.time_range = TimeRange(start_date=args.start_date, end_date=args.end_date)
        spider_logger.info(f"Spider mode: {args.mode}")
        background_tasks.add_task(spider_service.crawl, [args.url], rules)
        spider_logger.info(f"Running in background ...")
        
        return Response(message="ok", statusCode=200, status="success")
    
    except Exception as e:
        traceback.print_exc()
        spider_logger.error(f"Error: {e}")
        return Response(message=f"error: {e}", statusCode=500, status="failed")


@spider_controller.post("/migration-rank-spider/crawl-task", tags=["migration-rank-spider"], response_model=Response)
@inject
async def get_migration_rank(args: MigrationRankSpiderArgs,
                             background_tasks: BackgroundTasks,
                             spider_service: MigrationRankSpiderService = Depends(Provide[
                                 Application.services.migration_rank_spider_service]),
                             rules: ScrapeRules = Depends(load_config('migration_rank')),
                             yesterday: datetime = Depends(get_yesterday),
                             spider_logger: Logger = Depends(create_logger)):
    try:
        if len(args.url) == 0:
            spider_logger.error(f"No url is specified.")
            return Response(message="url should be specified", statusCode=400, status="failed")

        rules.mode = args.mode
        start_date = parser.parse(args.start_date) if type(
            args.start_date) is str else rules.time_range.start_date
        end_date = parser.parse(args.end_date) if type(
            args.end_date) is str else rules.time_range.end_date
        
        if rules.mode == 'history':
            rules.time_range = TimeRange(start_date=start_date, end_date=end_date)
        elif rules.mode == 'update':
            rules.time_range = TimeRange(
                start_date=yesterday, end_date=end_date)

        spider_logger.info(
            f"Start crawling {args.url} between {start_date} and {end_date}...")
        background_tasks.add_task(spider_service.crawl, [args.url], rules)
        spider_logger.info(f"Running in background ...")
        
        return Response(message="ok", statusCode=200, status="success")
    
    except Exception as e:
        traceback.print_exc()
        spider_logger.error(f"Error: {e}")
        return Response(message=f"error: {e}", statusCode=500, status="failed")
