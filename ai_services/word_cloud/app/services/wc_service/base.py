from abc import ABC, abstractmethod

class BaseWordCloudService(ABC):
    
    @abstractmethod
    def generate(self, text: str, top_k: int, with_weight: bool = True):
        pass


class BaseAsyncWordCloudService(ABC):

    @abstractmethod
    def generate(self, text: str, top_k: int, with_weight: bool = True):
        pass
