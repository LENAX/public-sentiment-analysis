from abc import ABC
from ..models.data_models import URL, DataModel
from typing import Any, List

class BaseSpiderService(ABC):
    """ Defines common interface for spider services.
    """

    def crawl(self, urls: List[URL], rules: Any, **kwargs) -> Any:
        return NotImplemented


class BaseCollectionService(ABC):
    """ Provides the common interface for accessing data in a collection
    """

    def add(self, data: DataModel) -> Any:
        return NotImplemented

    def get(self, query_condition: dict) -> DataModel:
        return NotImplemented

    def update(self, data: DataModel) -> Any:
        return NotImplemented

    def delete(self, query_condition: dict) -> DataModel:
        return NotImplemented


class BaseJobService(ABC):
    """ Provides the common interface for handling spider jobs
    """

    def add(self, job_spec: Any, worker: Any) -> Any:
        return NotImplemented

    def start(self, **kwargs) -> Any:
        return NotImplemented

    def get_state(self) -> Any:
        return NotImplemented


class BaseServiceFactory(ABC):
    """ Provides the common interface for creating services
    """

    def create(self, spec: Any, **kwargs) -> Any:
        return NotImplemented

    def register(self, name: str, product: Any, **kwargs) -> Any:
        return NotImplemented