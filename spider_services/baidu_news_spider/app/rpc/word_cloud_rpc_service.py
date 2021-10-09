import logging
import traceback
from typing import Optional
from spider_services.baidu_news_spider.app.rpc.models import NewsWordCloud
from spider_services.common.core.request_client import BaseRequestClient

from .base import RESTfulRPCService

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(funcName)s | %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S")
rpc_service_logger = logging.getLogger(__name__)
rpc_service_logger.setLevel(logging.DEBUG)


class WordCloudRPCService(RESTfulRPCService):

    def __init__(self, remote_service_endpoint: str,
                 request_client: BaseRequestClient,
                 response_model: NewsWordCloud,
                 logger: logging.Logger = rpc_service_logger):
        self._remote_service_endpoint = remote_service_endpoint
        self._request_client = request_client
        self._response_model = response_model
        self._logger = logger

    async def compute(self, theme_id: int, app_id: str) -> None:
        try:
            async with self._request_client.post(self._remote_service_endpoint,
                                                 json={"themeId": theme_id, "appId": app_id}) as resp:
                resp_data = await resp.json()

                if ('statusCode' in resp_data and resp_data['statusCode'] == 200):
                    self._logger.info("Compute task created successfully.")
                else:
                    self._logger.error("Failed to create compute task.")

        except Exception as e:
            traceback.print_exc()
            self._logger.error(e)
            raise e
