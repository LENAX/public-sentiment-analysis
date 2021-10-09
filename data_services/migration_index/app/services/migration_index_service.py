from typing import List
from pydantic import BaseModel
from .base_services import BaseAsyncCRUDService
from ..models.db_models import MigrationIndexDBModel
from ..models.data_models import MigrationIndex
import pandas as pd
import traceback
import logging
from logging import Logger

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(funcName)s | %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class MigrationIndexReportService(BaseAsyncCRUDService):
    """ Provides Migration Index Data Access
    """

    def __init__(self,
                 data_model: MigrationIndex,
                 db_model: MigrationIndexDBModel,
                 logger: Logger = logger):
        self._data_model = data_model
        self._db_model = db_model
        self._logger = logger
        
    def _to_dataframe(self, data: List[MigrationIndexDBModel]):
        data_list = [d.dict() for d in data]
        return pd.DataFrame(data_list)

    def _remove_duplicates(self, df):
        return df.sort_values(by=['date', "last_update"]).drop_duplicates(
            subset=["date", "areaCode", "migration_type"], keep='last')

    async def get_many(self, query: dict, page_size: int = 0, page_number: int = 0) -> List[MigrationIndex]:
        """ Get the most recent aqi report for db
        """
        try:
            # TODO: remove duplicate entries
            limit = page_size
            skip = page_size * page_number
            migration_indexes = await self._db_model.get(query, limit=limit, skip=skip)
            migration_index_df = self._to_dataframe(migration_indexes)
            unique_migration_rank_df = self._remove_duplicates(migration_index_df)
            return [self._data_model.parse_obj(report) for report in unique_migration_rank_df.to_dict(orient='records')]

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
        MigrationIndexDBModel.db = db_client['test']
        migration_index_report_service = MigrationIndexReportService(
            data_model=MigrationIndex, db_model=MigrationIndexDBModel)

        migration_indexes = await migration_index_report_service.get_many({
            'areaCode': '130100', 'date': {"$gte": '20210701'}}, page_size=30, page_number=1)

        debug(migration_indexes)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
