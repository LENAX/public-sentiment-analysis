from .base_notification_service import BaseAsyncNotificationService
from typing import Any, List
import aiohttp
import traceback
import logging
from logging import Logger

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(funcName)s | %(message)s",
                    datefmt="%Y-%m-%dT%H:%M:%S%z")
notification_service_logger = logging.getLogger(__name__)
notification_service_logger.setLevel(logging.DEBUG)


class HappyPAICNotificationService(BaseAsyncNotificationService):
    
    def __init__(self, happy_paic_server_url: str,
                 private_message_api_endpoint: str = "/api/im/happy-paic/text",
                 group_message_api_endpoint: str = "/api/im/happy-paic/group-text",
                 logger: Logger = notification_service_logger):
        self._happy_paic_server_url = happy_paic_server_url
        self._group_message_api = group_message_api_endpoint
        self._private_message_api = private_message_api_endpoint
        self._logger = logger
    
    async def _send_post_request(self, url: str, data: dict) -> dict:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=data) as response:
                    resp_data = await response.json()
                    return resp_data
        except Exception as e:
            traceback.print_exc()
            self._logger.error(f'{e}')
            raise e
    
    async def send(self, notification: str, receiver: str) -> bool:
        try:
            private_message_api = f"{self._happy_paic_server_url}/{self._private_message_api}"
            server_response = await self._send_post_request(
                private_message_api,
                {'text': notification, 'toUser': receiver})
            return server_response is not None and server_response['code'] == '000000'
        except Exception as e:
            traceback.print_exc()
            self._logger.error(f'{e}')
            raise e
    
    async def send_to_group(self, notification: str, group: List[str]) -> bool:
        try:
            group_message_api = f"{self._happy_paic_server_url}/{self._group_message_api}"
            server_response = await self._send_post_request(
                group_message_api, 
                {'text': notification, 'userList': group})
            return server_response is not None and server_response['code'] == '000000'
        except Exception as e:
            traceback.print_exc()
            self._logger.error(f'{e}')
            raise e

