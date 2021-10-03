import asyncio
import logging
import traceback
import pandas as pd
from itertools import chain
from typing import Callable, List

from data_services.news.app.models.db_models import NewsDBModel
from data_services.news.app.rpc.models.word_cloud_args import \
    WordCloudRequestArgs
from spider_services.common.core.request_client import BaseRequestClient

from ..models.data_models import WordCloud
from .base import RESTfulRPCService
from .models.word_cloud import WordCloud as WordCloudResponse

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(funcName)s | %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S")
rpc_service_logger = logging.getLogger(__name__)
rpc_service_logger.setLevel(logging.DEBUG)


class WordCloudGenerationService(RESTfulRPCService):

    def __init__(self, remote_service_endpoint: str,
                 request_client: BaseRequestClient,
                 request_model: WordCloudRequestArgs,
                 response_model: WordCloudResponse,
                 word_cloud_model: WordCloud,
                 gather: Callable = asyncio.gather,
                 data_frame: pd.DataFrame = pd.DataFrame,
                 chain: Callable = chain,
                 logger: logging.Logger = rpc_service_logger):
        self._remote_service_endpoint = remote_service_endpoint
        self._request_client = request_client
        self._request_model = request_model
        self._response_model = response_model
        self._word_cloud_model = word_cloud_model
        self._gather = gather
        self._data_frame = data_frame
        self._logger = logger
        
    async def _get_word_cloud(self, word_cloud_args: WordCloudRequestArgs) -> List[dict]:
        try:
            async with self._request_client.post(self._remote_service_endpoint,
                                                 json=word_cloud_args.dict()) as resp:
                resp_data = await resp.json()

                if (resp_data and 'data' in resp_data and
                    resp_data['data'] is not None and
                    'word_clouds' in resp_data['data'] and
                    type(resp_data['data']['word_clouds']) is list and
                    len(resp_data['data']['word_clouds']) > 0 and 
                    'statusCode' in resp_data and
                    resp_data['statusCode'] == 200):
                    return resp_data['data']['word_clouds']
                else:
                    self._logger.error(
                        f"Failed to create spider task! Response: {resp_data}")
                    return []
        except Exception as e:
            traceback.print_exc()
            self._logger.error(e)
            return []
        
    def _to_dataframe(self, word_clouds: List[List[dict]]):
        return self._data_frame(list(chain.from_iterable(word_clouds)))
    
    def _aggregate_weight(self, word_cloud_df):
        return word_cloud_df.groupby('word').sum()

    async def compute(self, news_list: List[NewsDBModel]) -> List[WordCloud]:
        try:
            request_arg_list = [self._request_model(
                theme_id=news.themeId, key_word=news.keyword,
                title=news.title, content=news.content
            ) for news in news_list]
            
            word_clouds = await self._gather(*[self._get_word_cloud(args) for args in request_arg_list])
            word_cloud_df = self._to_dataframe(word_clouds)
            aggregated_df = self._aggregate_weight(word_cloud_df)
            return [self._word_cloud_model.parse_obj(weighted_word)
                    for weighted_word in aggregated_df.to_dict(orient="records")]
        except Exception as e:
            traceback.print_exc()
            self._logger.error(e)
            return False
