import asyncio
from data_services.news.app.rpc.models.word_cloud_args import WordCloudRequestArgs
from data_services.news.app.rpc.request_client.request_client import RequestClient
from data_services.news.app.rpc.word_cloud_service import WordCloudGenerationService
import logging
import traceback
from datetime import datetime, timedelta
from logging import Logger
from typing import Callable, List

import pandas as pd
from data_services.news.app.services.news_service import NewsService

from ..models.data_models import NewsWordCloud, WordCloud
from ..models.db_models import WordCloudDBModel

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(funcName)s | %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S")
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class WordCloudService:
    """ Provides Word Cloud Data Access
    """

    def __init__(self,
                 data_model: NewsWordCloud,
                 db_model: WordCloudDBModel,
                 news_service: NewsService,
                 word_cloud_generation_service: WordCloudGenerationService,
                 gather: Callable = asyncio.gather,
                 logger: Logger = logger):
        self._data_model = data_model
        self._db_model = db_model
        self._news_service = news_service
        self._word_cloud_generation_service = word_cloud_generation_service
        self._gather = gather
        self._logger = logger
        
    async def get_one(self, theme_id: int) -> NewsWordCloud:
        try:
            word_cloud = await self._db_model.get_one({'themeId': theme_id})
            
            if word_cloud is None:
                return self._data_model(
                    theme_id=theme_id,
                    createDt=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    wordCloudPastWeek=[],
                    wordCloudPastMonth=[]
                )
            else:
                return self._data_model.parse_obj(word_cloud)
            
        except Exception as e:
            traceback.print_exc()
            self._logger.error(e)
            return self._data_model(
                theme_id=theme_id,
                createDt=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                wordCloudPastWeek=[],
                wordCloudPastMonth=[]
            )
            
    async def compute(self, theme_id: int) -> None:
        try:
            past_week = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            past_month = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            weekly_news, monthly_news = await self._gather(*[
                self._news_service.get_many(query={'themeId': theme_id, 'date': {'$gte': past_week}}),
                self._news_service.get_many(query={'themeId': theme_id, 'date': {'$gte': past_month}}),
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
            
            # only keep the first 40 words
            word_cloud = self._data_model(themeId=theme_id,
                                          createDt=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                          wordCloudPastWeek=weekly_word_cloud[:40],
                                          wordCloudPastMonth=monthly_word_cloud[:40])
            await self._db_model.update_one({'themeId': theme_id}, word_cloud.dict())
            
        except Exception as e:
            traceback.print_exc()
            self._logger.error(e)
            raise e 
        

if __name__ == "__main__":
    import asyncio

    from devtools import debug

    from ..db.client import create_client
    
    from ..models.data_models import News, WordCloud
    from ..models.db_models.news import NewsDBModel
    from ..rpc.models.word_cloud import WordCloud as WordCloudResponse

    async def main():
        db_client = create_client(host='localhost',
                                  username='admin',
                                  password='root',
                                  port=27017,
                                  db_name='test')
        NewsDBModel.db = db_client['test']
        async with (await RequestClient()) as client_session:
            news_service = NewsService(data_model=News, db_model=NewsDBModel)
            word_cloud_generation_service = WordCloudGenerationService(
                remote_service_endpoint='http://localhost:9000/wordcloud',
                request_client=client_session,
                request_model=WordCloudRequestArgs,
                response_model=WordCloudResponse,
                word_cloud_model=WordCloud
            )

            word_cloud_service = WordCloudService(data_model=NewsWordCloud,
                                                  news_service=news_service,
                                                  word_cloud_generation_service=word_cloud_generation_service)

            word_cloud = await word_cloud_service.compute(theme_id=0)

            debug(word_cloud)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
