from spider_services.common.core.request_client import BaseRequestClient


class RESTfulRPCService(object):
    
    def __init__(self, remote_service_endpoint: str, request_client: BaseRequestClient):
        self._remote_service_endpoint = remote_service_endpoint
        self._request_client = request_client

