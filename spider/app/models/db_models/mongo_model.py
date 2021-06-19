from pydantic import BaseModel, parse
from bson import ObjectId
from datetime import datetime
from typing import Optional, Any, List
from ...db import AsyncMongoCRUDBase
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from uuid import UUID


class MongoModel(BaseModel, AsyncMongoCRUDBase):

    __collection__: str = ""
    __db__: AsyncIOMotorDatabase = None

    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            ObjectId: lambda oid: str(oid),
        }

    @property
    def collection(cls) -> AsyncIOMotorCollection:
        return cls.__db__[cls.__collection__]

    @collection.setter
    def collection(cls, collection_name):
        cls.__collection__ = collection_name

    @property
    def db(cls):
        return cls.__db__

    @db.setter
    def db(cls, db_client_instance):
        cls.__db__ = db_client_instance

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

        # parsed = self.dict(
        #     exclude_unset=exclude_unset,
        #     by_alias=by_alias,
        #     **kwargs,
        # )
        parsed = self.todict(
            self,
            exclude_unset=exclude_unset,
            by_alias=by_alias,
            **kwargs,
        )

        parsed.pop("__collection__", None)
        parsed.pop("__db__", None)

        # Mongo uses `_id` as default key. We should stick to that as well.
        if '_id' not in parsed and 'id' in parsed:
            parsed['_id'] = parsed.pop('id')

        return parsed

    @classmethod
    def todict(cls, obj, classkey=None, **kwargs):
        exclude_unset = kwargs.pop('exclude_unset', True)
        by_alias = kwargs.pop('by_alias', True)

        if isinstance(obj, dict):
            data = {}
            for (k, v) in obj.items():
                data[k] = cls.todict(
                    v, classkey,
                    exclude_unset=exclude_unset,
                    by_alias=by_alias)
            return data
        elif type(obj) is UUID:
            return str(obj)
        elif hasattr(obj, "_ast"):
            return cls.todict(obj._ast(),
                    exclude_unset=exclude_unset,
                    by_alias=by_alias)
        elif hasattr(obj, "__dict__"):
            data = dict([(key, cls.todict(value, classkey,
                    exclude_unset=exclude_unset,
                    by_alias=by_alias)) 
                for key, value in obj.__dict__.items() 
                if not callable(value) and not key.startswith('_')])
            if classkey is not None and hasattr(obj, "__class__"):
                data[classkey] = obj.__class__.__name__
            return data
        elif hasattr(obj, "__iter__") and not isinstance(obj, str):
            return [cls.todict(v, classkey,
                    exclude_unset=exclude_unset,
                    by_alias=by_alias) for v in obj]
        else:
            return obj
    
    @classmethod
    async def insert_many(cls, data: List[BaseModel], **kwargs):
        try:
            await cls.db[cls.__collection__].insert_many([d.mongo() for d in data])
        except Exception as e:
            print(e)

    @classmethod
    async def get(cls, query: Any) -> List[object]:
        try:
            query_result = await cls.__db__[cls.__collection__].find(query)
            result = [cls.from_mongo(data) for data in query_result]
            return result
        except AttributeError as e:
            print(e("You must set db instance before getting any data"))
            return []

    async def save(self):
        try:
            result = await self.db[self.__collection__].insert_one(self.mongo())
        except Exception as e:
            print(e)


if __name__ == "__main__":
    general_mongo_model = MongoModel()
    print(dir(general_mongo_model))