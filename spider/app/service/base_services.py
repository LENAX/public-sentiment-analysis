from abc import ABC
from ..models.data_models import URL, DataModel
from typing import Any, List

class BaseSpiderService(ABC):
    """ Defines common interface for spider services.
    """

    def get(data_src: URL) -> Any:
        return NotImplemented

    def get_many(data_src: List[URL]) -> Any:
        return NotImplemented


class BaseCollectionService(ABC):
    """ Provides the common interface for accessing data in a collection
    """

    def add(data: DataModel) -> Any:
        return NotImplemented

    def get(query_condition: dict) -> DataModel:
        return NotImplemented

    def update(data: DataModel) -> Any:
        return NotImplemented

    def delete(query_condition: dict) -> DataModel:
        return NotImplemented
