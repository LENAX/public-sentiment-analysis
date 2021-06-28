from abc import ABC, abstractmethod
from ..models.data_models import URL, DataModel
from typing import List, Any, Callable
from pydantic import BaseModel
from ..models.request_models import QueryArgs

class BaseSpiderService(ABC):
    """ Defines common interface for spider services.
    """

    @abstractmethod
    def crawl(self, urls: List[URL], rules: Any, **kwargs) -> Any:
        return NotImplemented


class BaseAsyncCRUDService(ABC):
    """ Provides the common interface for doing CRUD
    """
    @abstractmethod
    async def add_one(self, data: BaseModel) -> BaseModel:
        return NotImplemented

    @abstractmethod
    async def add_many(self, data_list: List[BaseModel]) -> List[BaseModel]:
        return NotImplemented

    @abstractmethod
    async def get_one(self, id: str) -> BaseModel:
        return NotImplemented

    @abstractmethod
    async def get_many(self, query: QueryArgs) -> List[BaseModel]:
        return NotImplemented

    @abstractmethod
    async def update_one(self, id: str, update_data: BaseModel) -> None:
        pass

    @abstractmethod
    async def update_many(self, query: QueryArgs, data_list: List[BaseModel]) -> None:
        pass

    @abstractmethod
    async def delete_one(self, id: str) -> None:
        pass

    @abstractmethod
    async def delete_many(self, query: QueryArgs) -> None:
        pass


class BaseJobService(ABC):
    """ Provides the common interface for handling spider jobs
    """
    @abstractmethod
    def add_job(self, func: Callable, **kwargs) -> Any:
        return NotImplemented

    @abstractmethod
    def update_job(self, job_id: str, **kwargs) -> Any:
        return NotImplemented

    @abstractmethod
    def delete_job(self, job_id: str) -> Any:
        return NotImplemented

    @abstractmethod
    def get_job(self, job_id: str) -> Any:
        return NotImplemented


class BaseServiceFactory(ABC):
    """ Provides the common interface for creating services
    """

    @abstractmethod
    def create(self, spec: Any, **kwargs) -> Any:
        return NotImplemented

    @abstractmethod
    def register(self, name: str, product: Any, **kwargs) -> Any:
        return NotImplemented
