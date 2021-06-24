from abc import ABC, abstractmethod
from ..models.data_models import URL, DataModel
from typing import List, Any, Callable

class BaseSpiderService(ABC):
    """ Defines common interface for spider services.
    """

    @abstractmethod
    def crawl(self, urls: List[URL], rules: Any, **kwargs) -> Any:
        return NotImplemented


class BaseCollectionService(ABC):
    """ Provides the common interface for accessing data in a collection
    """
    @abstractmethod
    def add(self, data: DataModel) -> Any:
        return NotImplemented

    @abstractmethod
    def get(self, query_condition: dict) -> DataModel:
        return NotImplemented

    @abstractmethod
    def update(self, data: DataModel) -> Any:
        return NotImplemented

    @abstractmethod
    def delete(self, query_condition: dict) -> DataModel:
        return NotImplemented


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
