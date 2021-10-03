from data_services.news.app.rpc.models.spider_args import BaiduNewsSpiderArgs
from ..models.db_models import ThemeDBModel
import logging
import traceback
from typing import Optional
from typing_extensions import Literal
from spider_services.common.core.request_client import BaseRequestClient

from .base import RESTfulRPCService

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(funcName)s | %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S")
rpc_service_logger = logging.getLogger(__name__)
rpc_service_logger.setLevel(logging.DEBUG)


class NewsSpiderService(RESTfulRPCService):

    def __init__(self, remote_service_endpoint: str,
                 request_client: BaseRequestClient,
                 request_model: BaiduNewsSpiderArgs,
                 logger: logging.Logger = rpc_service_logger):
        self._remote_service_endpoint = remote_service_endpoint
        self._request_client = request_client
        self._request_model = request_model
        self._logger = logger

    async def crawl(self, theme: ThemeDBModel, mode: Literal['update', 'history']) -> bool:
        try:
            request_args = self._request_model(
                past_days=3 if mode == 'update' else 30,
                theme_id=theme.themeId,
                area_keywords=theme.areaKeywords,
                theme_keywords=theme.themeKeywords,
                epidemic_keywords=theme.epidemicKeywords
            )
            async with self._request_client.post(self._remote_service_endpoint,
                                                 json=request_args.dict()) as resp:
                resp_data = await resp.json()

                if ('statusCode' in resp_data and resp_data['statusCode'] == 200):
                    self._logger.info(f"response: {resp_data}")
                    return True
                else:
                    self._logger.error(
                        f"Failed to create spider task! Response: {resp_data}")
                    return False

        except Exception as e:
            traceback.print_exc()
            self._logger.error(e)
            return False
