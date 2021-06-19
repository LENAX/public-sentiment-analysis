""" CRUD Base Class
"""
from typing import Any, List


class AsyncCRUDBase(object):

    @staticmethod
    async def get(db: Any, query: Any, **kwargs):
        return NotImplemented

    @staticmethod
    async def delete(db: Any, query: Any, **kwargs):
        return NotImplemented

    @staticmethod
    async def insert_many(db: Any, data: Any, **kwargs):
        return NotImplemented

    async def save(self, db, collection):
        return NotImplemented


class AsyncMongoCRUDBase(AsyncCRUDBase):
    """ Provides minimal support for writing to MongoDB
    """
    
    @staticmethod
    async def get(collection: Any,  query: Any, **kwargs) -> List[object]:
        result = [data async for data in collection.find(query)]
        return result

    @staticmethod
    async def delete(collection: Any, query: Any, **kwargs):
        return NotImplemented

    @staticmethod
    async def insert_many(collection: Any, data: Any, **kwargs):
        await collection.insert_many(data)

    async def save(self, collection):
        return NotImplemented
