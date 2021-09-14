from typing import List, Any, Coroutine
from pydantic import parse_obj_as, BaseModel
from .base_services import BaseAsyncCRUDService
from ..models.db_models import CMAWeatherReportDBModel, AirQualityDBModel
from ..models.data_models import WeatherAQI, CMAWeatherReport, CMADailyWeather
import numpy as np
import pandas as pd
import traceback
import logging
from logging import Logger, getLogger

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(funcName)s |%(message)s",
                    datefmt="%Y-%m-%dT%H:%M:%S%z")
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class CMAWeatherReportService(BaseAsyncCRUDService):
    """ Provides CMA Daily Weather Data Access
    """

    def __init__(self,
                 cma_daily_weather_data_model: CMADailyWeather,
                 cma_weather_report_data_model: CMAWeatherReport,
                 cma_weather_report_db_model: CMAWeatherReportDBModel,
                 logger: Logger = logger):
        self._output_model = cma_daily_weather_data_model
        self._data_model = cma_weather_report_data_model
        self._db_model = cma_weather_report_db_model
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

    async def get_many(self, query: dict) -> List[CMADailyWeather]:
        try:
            # query should include province, city, start date and end date
            group_args = {key: {'$first': f"${key}"}
                          for key in self._data_model.schema()['properties']}
            pipeline = [
                {"$sort": {"lastUpdate": -1}},
                {"$match": query},
                {"$group": {
                    "_id": "$location.locationId",
                    **group_args
                }}
            ]
            cma_weather_reports = await self._db_model.aggregate(pipeline)
            if len(cma_weather_reports) == 0:
                return []
            
            weather_df = self._to_dataframe(cma_weather_reports)
            weather_mean = weather_df.groupby(['province', 'city', 'areaCode']).mean()
            weather_max = weather_df.groupby(['province', 'city', 'areaCode']).max()
            weather_min = weather_df.groupby(['province', 'city', 'areaCode']).min()
            
            cma_daily_weather_stats = []
            for row in weather_mean.iterrows():
                province, city, areaCode = row[0]
                mean_weather_series = row[1]
                min_weather_series = weather_min.loc[(province, city, areaCode), :]
                max_weather_series = weather_max.loc[(province, city, areaCode), :]
                
                weather_stats = self._output_model(
                    avgAirPressure=mean_weather_series['pressure'],
                    avgDailyWindSpeed=mean_weather_series['windSpeed'],
                    avgRelativeHumidity=mean_weather_series['humidity'],
                    avgTemperature=mean_weather_series['temperature'],
                    maxAirPressure=max_weather_series['pressure'],
                    maxHumidity=max_weather_series['humidity'],
                    maxTemperature=max_weather_series['temperature'],
                    minAirPressure=min_weather_series['pressure'],
                    minHumidity=min_weather_series['humidity'],
                    minTemperature=min_weather_series['temperature'],
                    precipitation=mean_weather_series['precipitation'],
                    province=province,
                    city=city,
                    areaCode=areaCode
                )
                
                cma_daily_weather_stats.append(weather_stats)
            
            return cma_daily_weather_stats

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
        CMAWeatherReportDBModel.db = db_client['test']
        cma_weather_report_service = CMAWeatherReportService(
            cma_daily_weather_data_model=CMADailyWeather,
            cma_weather_report_data_model=CMAWeatherReport,
            cma_weather_report_db_model=CMAWeatherReportDBModel
        )
        
        # results = await CMAWeatherReportDBModel.get({'location.province': '广东'})
        # debug(results)
        weather_reports = await cma_weather_report_service.get_many({
            'location.province': '湖北', 'create_dt': {"$gte": '2021-09-14'}})

        debug(weather_reports)
        
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
