from typing import List, Any, Coroutine
from pydantic import parse_obj_as, BaseModel
from .base_services import BaseAsyncCRUDService
from ..models.db_models import AirQualityDBModel
from ..models.data_models import AirQuality
import numpy as np
import pandas as pd
import traceback
import logging
from logging import Logger, getLogger

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(funcName)s |%(message)s",
                    datefmt="%Y-%m-%dT%H:%M:%S%z")
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class AQIReportService(BaseAsyncCRUDService):
    """ Provides Air Quality Data Access
    """

    def __init__(self,
                 data_model: AirQuality,
                 db_model: AirQualityDBModel,
                 logger: Logger = logger):
        self._data_model = data_model
        self._db_model = db_model
        self._logger = logger

    def _to_dataframe(self, cma_weather_data):
        cma_weather_reports = [self._data_model.parse_obj(
            report) for report in cma_weather_data]
        weather_data = []
        for report in cma_weather_reports:
            weather = report.dict()
            weather['province'] = report.location.province
            weather['city'] = report.location.city
            weather['areaCode'] = report.location.areaCode
            weather_data.append(weather)

        return pd.DataFrame(weather_data)

    async def get_many(self, query: dict) -> List[AirQuality]:
        """ Get the most recent aqi report for db
        """
        try:
            group_args = {key: {'$first': f"${key}"}
                          for key in self._data_model.schema()['properties']}
            pipeline = [
                {"$sort": {"lastUpdate": -1}},
                {"$match": query},
                {"$group": {
                    "_id": "$city",
                    **group_args
                }}
            ]
            
            aqi_reports = await self._db_model.aggregate(pipeline)
            return [self._data_model.parse_obj(report) for report in aqi_reports]

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
        AirQualityDBModel.db = db_client['test']
        aqi_report_service = AQIReportService(
            data_model=AirQuality, db_model=AirQualityDBModel)

        # results = await CMAWeatherReportDBModel.get({'location.province': '广东'})
        # debug(results)
        aqi_reports = await aqi_report_service.get_many({
            'province': '湖北', 'create_dt': {"$gte": '2021-09-10'}})

        debug(aqi_reports)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
