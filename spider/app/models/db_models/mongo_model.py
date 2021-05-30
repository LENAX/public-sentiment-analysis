from pydantic import BaseModel
from bson import ObjectId
from datetime import datetime
from typing import Optional
from ...db import AsyncMongoCRUDBase

class MongoModel(BaseModel, AsyncMongoCRUDBase):

    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            ObjectId: lambda oid: str(oid),
        }

    @classmethod
    def from_mongo(cls, data: dict):
        """We must convert _id into "id". """
        if not data:
            return data
        id = data.pop('_id', None)
        return cls(**dict(data, id=id))

    def mongo(self, **kwargs):
        exclude_unset = kwargs.pop('exclude_unset', True)
        by_alias = kwargs.pop('by_alias', True)

        parsed = self.dict(
            exclude_unset=exclude_unset,
            by_alias=by_alias,
            **kwargs,
        )

        # Mongo uses `_id` as default key. We should stick to that as well.
        if '_id' not in parsed and 'id' in parsed:
            parsed['_id'] = parsed.pop('id')

        return parsed
    
    @staticmethod
    async def insert_many(to_collection: Any, data: List[MongoModel], **kwargs):
        await to_collection.insert_many([d.mongo() for d in data])

    @classmethod
    async def get(cls, collection: Any,  query: Any, **kwargs) -> List[object]:
        result = [cls.from_mongo(data) async for data in collection.find(query)]
        return result

    async def save(self, db, collection_name:str):
        try:
            await db[collection_name].insert_one(self.mongo())
        except Exception as e:
            print(e)