from abc import ABC, abstractmethod
from aiohttp import ClientSession
from typing import Any

class BaseRequestClient(ABC):
    """ Base class all request client classes
    """

    @abstractmethod
    def get(self, url: str, params: dict = {}) -> Any:
        return NotImplemented

class RequestClient(BaseRequestClient, ClientSession):
    """ Handles HTTP Request and Connection Pooling
    """
    pass
