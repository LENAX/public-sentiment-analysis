""" Holds a shared aiohttp ClientSession
"""

from aiohttp import ClientSession
from singleton_decorator import singleton
from .models.data_models import (
    RequestHeader
)

@singleton
class SessionHolder:
    def __init__(self, headers: RequestHeader):
        self.session = ClientSession(headers=headers)

    @property.getter
    def session(self):
        return self.session
