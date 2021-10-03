from abc import ABC, abstractmethod
from typing import List, Any, Callable
from pydantic import BaseModel


class BaseAsyncCRUDService(ABC):
    """ Provides the common interface for doing CRUD
    """
    @abstractmethod
    async def add_one(self, data: BaseModel):
        return NotImplemented

    @abstractmethod
    async def add_many(self, data_list: List[BaseModel]):
        return NotImplemented

    @abstractmethod
    async def get_one(self, query: dict) -> BaseModel:
        return NotImplemented

    @abstractmethod
    async def get_many(self, query: dict) -> List[BaseModel]:
        return NotImplemented

    @abstractmethod
    async def update_one(self, query: dict, update_data: BaseModel) -> None:
        pass

    @abstractmethod
    async def update_many(self, query: dict, data_list: List[BaseModel]) -> None:
        pass

    @abstractmethod
    async def delete_one(self, query: dict) -> None:
        pass

    @abstractmethod
    async def delete_many(self, query: dict) -> None:
        pass
