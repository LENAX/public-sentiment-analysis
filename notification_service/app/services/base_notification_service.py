from abc import ABC, abstractmethod
from typing import Any

class BaseNotificationService(ABC):
    
    @abstractmethod
    def send(self, notification: Any, receiver: Any) -> bool:
        pass
    
    @abstractmethod
    def send_to_group(self, notification: Any, group: Any) -> bool:
        pass


class BaseAsyncNotificationService(ABC):

    @abstractmethod
    async def send(self, notification: Any, receiver: Any) -> bool:
        pass

    @abstractmethod
    async def send_to_group(self, notification: Any, group: Any) -> bool:
        pass
