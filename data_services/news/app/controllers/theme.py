from fastapi import APIRouter, Depends
from ..models.response_models import Response
from ..models.data_models import MigrationIndex, MigrationRank
from ..models.db_models import MigrationIndexDBModel, MigrationRankDBModel
from typing import Optional, List
from dependency_injector.wiring import inject, Provide
from ..container import Application
from ..services import MigrationIndexReportService, MigrationRankReportService
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

migration_report_controller = APIRouter()


@migration_report_controller.get('/migration-index', tags=["migration-index"], response_model=Response[List[MigrationIndex]])
@inject
async def get_migration_index(areaCode: Optional[str] = None, startDate: str = get_past_n_days(1), 
                              endDate: str = get_past_n_days(0),
                              migrationType: Optional[str] = None,
                              pageSize: int = 30, pageNumber: int = 0,
                              migration_index_service: MigrationIndexReportService = Depends(Provide[
                                  Application.services.migration_index_report_service]),
                              logger: Logger = Depends(create_logger)):
    try:
        # could be refactored to a query builder method
        required_args = {'date': {'$gte': startDate, '$lte': endDate}}
        optional_args = {'areaCode': areaCode, 'migration_type': migrationType}
        query = {**required_args,
                 **{key: optional_args[key]
                    for key in optional_args if optional_args[key] is not None}}
        logger.info(f"query: {query}")
        migration_indexes = await migration_index_service.get_many(query, page_size=pageSize, page_number=pageNumber)
        logger.info(f"migration_indexes: {migration_indexes}")
        return Response[List[MigrationIndex]](data=migration_indexes, message='ok', statusCode=200, status='success')
    except Exception as e:
        traceback.print_exc()
        logger.error(f"{e}")
        return Response(message=f"{e}", statusCode=500, status="failed")


@migration_report_controller.get('/migration-rank', tags=["migration-index"], response_model=Response[List[MigrationRank]])
@inject
async def get_migration_rank(from_province: Optional[str] = None, to_province: Optional[str] = None,
                             from_province_areaCode: Optional[str] = None, to_province_areaCode: Optional[str] = None,
                             startDate: str = get_past_n_days(1), endDate: str = get_past_n_days(0),
                             direction: Optional[str] = None,
                             pageSize: int = 30, pageNumber: int = 0,
                             migration_rank_service: MigrationRankReportService = Depends(Provide[
                                Application.services.migration_rank_report_service]),
                             logger: Logger = Depends(create_logger)):
    try:
        required_args = {'date': {'$gte': startDate, '$lte': endDate}}
        optional_args = {'from_province': from_province, 'to_province': to_province,
                         'from_province_areaCode': from_province_areaCode, 'to_province_areaCode': to_province_areaCode,
                         'direction': direction}
        query = {**required_args,
                 **{key: optional_args[key]
                    for key in optional_args if optional_args[key] is not None}}
        logger.info(f"query: {query}")
        migration_ranks = await migration_rank_service.get_many(query, page_size=pageSize, page_number=pageNumber)
        logger.info(f"migration_ranks: {migration_ranks}")
        return Response[List[MigrationRank]](data=migration_ranks, message='ok', statusCode=200, status='success')
    except Exception as e:
        traceback.print_exc()
        logger.error(f"{e}")
        return Response(message=f"{e}", statusCode=500, status="failed")
