""" CRUD Base Class
"""
from abc import ABC, abstractmethod
from typing import Any, List


class AsyncCRUDBase(ABC):

    @abstractmethod
    async def get(db: Any, query: Any, **kwargs):
        return NotImplemented

    @abstractmethod
    async def delete(db: Any, query: Any, **kwargs):
        return NotImplemented

    @abstractmethod
    async def insert_many(db: Any, data: Any, **kwargs):
        return NotImplemented

    @abstractmethod
    async def save(self, db, collection):
        return NotImplemented


class AsyncMongoCRUDBase(AsyncCRUDBase):
    """ Provides minimal support for writing to MongoDB
    """
    
    @staticmethod
    async def get(collection: Any,  query: Any, **kwargs) -> List[object]:
        cursor = collection.find(query)
        result = await cursor.to_list()
        return result

    @staticmethod
    async def delete(collection: Any, query: Any, **kwargs) -> None:
        result = await collection.delete_many(query)
        print(f"Deleted {result.deleted_count} items.")

    @staticmethod
    async def insert_many(collection: Any, data: Any, **kwargs) -> None:
        await collection.insert_many(data)

