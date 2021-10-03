import asyncio
from data_services.news.app.rpc.word_cloud_service import WordCloudGenerationService
import logging
import traceback
from datetime import datetime, timedelta
from logging import Logger
from typing import Callable, List

import pandas as pd
from data_services.news.app.services.news_service import NewsService

from ..models.data_models import NewsWordCloud, WordCloud

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(funcName)s | %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class WordCloudService:
    """ Provides Word Cloud Data Access
    """

    def __init__(self,
                 data_model: NewsWordCloud,
                 news_service: NewsService,
                 word_cloud_generation_service: WordCloudGenerationService,
                 gather: Callable = asyncio.gather,
                 logger: Logger = logger):
        self._data_model = data_model
        self._news_service = news_service
        self._word_cloud_generation_service = word_cloud_generation_service
        self._gather = gather
        self._logger = logger

    async def compute(self, theme_id: int) -> NewsWordCloud:
        try:
            past_week = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            past_month = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            weekly_news, monthly_news = await self._gather(*[
                self._news_service.get_many({'theme_id': theme_id, 'date': {'$gte': past_week}}),
                self._news_service.get_many({'theme_id': theme_id, 'date': {'$gte': past_month}}),
            ])
            
            if not all([type(weekly_news) is list,
                        len(weekly_news) > 0,
                        type(monthly_news) is list,
                        len(monthly_news) > 0]):
                self._logger.error(f"Failed to get weekly news or monthly news.")
                self._logger.error(f"weekly_news: {weekly_news}")
                self._logger.error(f"monthly_news: {monthly_news}")
                return self._data_model(
                    theme_id=theme_id,
                    createDt=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    wordCloudPastWeek=[],
                    wordCloudPastMonth=[]
                )
                
            weekly_word_cloud, monthly_word_cloud = await self._gather(*[
                self._word_cloud_generation_service.compute(weekly_news),
                self._word_cloud_generation_service.compute(monthly_news)
            ])
            
            if not all([type(weekly_word_cloud) is list,
                        len(weekly_word_cloud) > 0 and type(weekly_word_cloud[0]) is WordCloud,
                        type(monthly_word_cloud) is list,
                        len(monthly_word_cloud) > 0 and type(monthly_word_cloud[0]) is WordCloud]):
                self._logger.error(f"Failed to get weekly word cloud or monthly word cloud.")
                self._logger.error(f"weekly_news: {weekly_word_cloud}")
                self._logger.error(f"monthly_news: {monthly_word_cloud}")
                return self._data_model(
                    theme_id=theme_id,
                    createDt=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    wordCloudPastWeek=[],
                    wordCloudPastMonth=[]
                )
                
            return self._data_model(theme_id=theme_id,
                                    createDt=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    wordCloudPastWeek=weekly_word_cloud,
                                    wordCloudPastMonth=monthly_word_cloud)
            
        except Exception as e:
            traceback.print_exc()
            self._logger.error(e)
            return self._data_model(
                theme_id=theme_id,
                createDt=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                wordCloudPastWeek=[],
                wordCloudPastMonth=[]
            )
        

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
