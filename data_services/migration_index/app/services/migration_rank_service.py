from typing import List
from pydantic import BaseModel
from .base_services import BaseAsyncCRUDService
from ..models.db_models import MigrationRankDBModel
from ..models.data_models import MigrationRank
import pandas as pd
import traceback
import logging
from logging import Logger

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(funcName)s | %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class MigrationRankReportService(BaseAsyncCRUDService):
    """ Provides Migration Index Data Access
    """

    def __init__(self,
                 data_model: MigrationRank,
                 db_model: MigrationRankDBModel,
                 logger: Logger = logger):
        self._data_model = data_model
        self._db_model = db_model
        self._logger = logger

    async def get_many(self, query: dict, page_size: int = 0, page_number: int = 0) -> List[MigrationRank]:
        """ Get the most recent aqi report for db
        """
        try:
            # TODO: remove duplicate entries
            limit = page_size
            skip = page_size * page_number
            migration_ranks = await self._db_model.get(query, limit=limit, skip=skip)
            return [self._data_model.parse_obj(report) for report in migration_ranks]

        except Exception as e:
            traceback.print_exc()
            self._logger.error(f"Error: {e}")
            return []

    async def add_one(self, data: BaseModel) -> BaseModel:
        return NotImplemented

    async def add_many(self, data_list: List[BaseModel]) -> List[BaseModel]:
        return NotImplemented

    async def get_one(self, id: str) -> BaseModel:
        return NotImplemented

    async def update_one(self, id: str, update_data: BaseModel) -> None:
        pass

    async def update_many(self, query: dict, data_list: List[BaseModel]) -> None:
        pass

    async def delete_one(self, id: str) -> None:
        pass

    async def delete_many(self, query: dict) -> None:
        pass


if __name__ == "__main__":
    import asyncio
    from devtools import debug
    from ..db import create_client

    async def main():
        db_client = create_client(host='localhost',
                                  username='admin',
                                  password='root',
                                  port=27017,
                                  db_name='test')
        MigrationRankDBModel.db = db_client['test']
        migration_rank_report_service = MigrationRankReportService(
            data_model=MigrationRank, db_model=MigrationRankDBModel)

        migration_ranks = await migration_rank_report_service.get_many({
            'from_province': '湖北省',
            'date': {"$gte": '20210923'},
            'direction': 'move_in'}, page_size=30, page_number=1)

        debug(migration_ranks)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
