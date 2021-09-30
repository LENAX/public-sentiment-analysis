import logging
import traceback
from typing import Optional
from spider_services.common.core.request_client import BaseRequestClient

from .base import RESTfulRPCService

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(funcName)s | %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S")
rpc_service_logger = logging.getLogger(__name__)
rpc_service_logger.setLevel(logging.DEBUG)


class ArticleClassificationService(RESTfulRPCService):

    def __init__(self, remote_service_endpoint: str,
                 request_client: BaseRequestClient,
                 logger: logging.Logger = rpc_service_logger):
        self._remote_service_endpoint = remote_service_endpoint
        self._request_client = request_client
        self._logger = logger

    async def is_medical_article(self, theme_id: int, keyword: str, title: str, content: str) -> Optional[bool]:
        try:
            async with self._request_client.post(self._remote_service_endpoint, json={
                    "theme_id": theme_id, "keyword": keyword, "title": title, "content": content}) as resp:
                resp_data = await resp.json()

                if (resp_data and 'data' in resp_data and resp_data['data'] is not None and 'status' in resp_data['status'] == 200 and
                    'whether_medical_result' in resp_data['data']):
                    return resp_data['data']['whether_medical_result'] == 1
                else:
                    self._logger.error(
                        f"Failed to receive article summary data from remote server! Response: {resp_data}")
                    return False

        except Exception as e:
            traceback.print_exc()
            self._logger.error(e)
            raise e
