from pydantic import BaseModel, parse
from bson import ObjectId
from datetime import datetime, date
from typing import Optional, Any, List, Union
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from uuid import UUID
from enum import Enum
from devtools import debug
import traceback


class MongoModel(BaseModel):
    """ Provides base for all other database models
    """

    __collection__: str = ""
    __db__: AsyncIOMotorDatabase = None

    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            ObjectId: lambda oid: str(oid),
        }

    @property
    def collection(self) -> AsyncIOMotorCollection:
        return self.db[self.__collection__]

    @collection.setter
    def collection(self, collection_name):
        self.__collection__ = collection_name

    @property
    def db(self):
        return self.__db__

    @db.setter
    def db(self, db_client_instance):
        self.__db__ = db_client_instance

    @classmethod
    def from_mongo(cls, data: dict) -> Union["MongoModel", None]:
        """We must convert _id into "id". """
        if not data:
            return None
        id = data.pop('_id', None)
        parsed = cls(**dict(data))
        setattr(parsed, "id", id)
        return parsed

    def mongo(self, **kwargs):
        exclude_unset = kwargs.pop('exclude_unset', True)
        by_alias = kwargs.pop('by_alias', True)

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
    def todict(cls, obj, classkey=None, **kwargs) -> dict:
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
        elif (type(obj) is UUID or
              isinstance(obj, Enum) or
              isinstance(obj, date)):
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
    def parse_many(cls, obj_list: List[BaseModel]) -> List["MongoModel"]:
        try:
            parsed_models = [cls.parse_obj(model_instance) for model_instance in obj_list]
            return parsed_models
        except Exception as e:
            raise e
    
    @classmethod
    async def insert_many(cls, data: List["MongoModel"], **kwargs):
        try:
            await cls.db[cls.__collection__].insert_many([d.mongo() for d in data])
        except Exception as e:
            print(e)
            
    @classmethod
    async def bulk_write(cls, requests):
        try:
            print(f"Bulk writing {len(requests)} items")
            result = await cls.db[cls.__collection__].bulk_write(requests)
            if result:
                print(f"Successfully matched {result.matched_count}"
                      f" and updated {result.modified_count} records.")
        except Exception as e:
            traceback.print_exc()
            print(e)

    @classmethod
    async def aggregate(cls, pipeline: List[dict]) -> List["MongoModel"]:
        try:
            cursor = cls.db[cls.__collection__].aggregate(pipeline)
            agg_results = [cls.from_mongo(result) async for result in cursor]
            return agg_results
        except Exception as e:
            traceback.print_exc()
            raise e

    @classmethod
    async def get(cls, query: dict,
                  limit: Optional[int] = 0,
                  skip: Optional[int] = 0) -> List["MongoModel"]:
        try:
            query_result = cls.db[cls.__collection__].find(query, limit=limit, skip=skip)
            result = [cls.from_mongo(data) async for data in query_result]
            return result
        except AttributeError as e:
            print("You must set db instance before getting any data")
            raise e

    @classmethod
    async def get_one(cls, query: dict) -> "MongoModel":
        try:
            result = await cls.db[cls.__collection__].find_one(query)
            return cls.from_mongo(result)
        except AttributeError as e:
            print("You must set db instance before getting any data")
            raise e

    @classmethod
    async def delete_many(cls, query: dict) -> None:
        try:
            delete_result = await cls.db[cls.__collection__].delete_many(query)
            if delete_result:
                print(
                    f"Successfully deleted {delete_result.deleted_count} records.")
        except AttributeError as e:
            print("You must set db instance before getting any data")
            raise e

    @classmethod
    async def delete_one(cls, query: dict) -> None:
        try:
            delete_result = await cls.db[cls.__collection__].delete_one(query)
            if delete_result:
                print(
                    f"Successfully deleted {delete_result.deleted_count} records.")
        except AttributeError as e:
            print("You must set db instance before getting any data")
            raise e

    @classmethod
    async def update_many(cls, filter: dict, update: dict) -> None:
        try:
            update_result = await cls.db[cls.__collection__].update_many(filter, {"$set":update})
            if update_result:
                print(
                    f"Successfully matched {update_result.matched_count}"
                    f" and updated {update_result.modified_count} records.")
        except AttributeError as e:
            print("You must set db instance before getting any data")
            raise e
        
    

    @classmethod
    async def update_one(cls, filter: dict, update: dict, upsert: bool = True) -> None:
        try:
            update_result = await cls.db[cls.__collection__].update_one(filter, {"$set":update}, upsert=upsert)
            if update_result:
                print(
                    f"Successfully matched {update_result.matched_count}"
                    f" and updated {update_result.modified_count} records.")
        except AttributeError as e:
            print("You must set db instance before getting any data")
            raise e

    async def save(self):
        try:
            result = await self.db[self.__collection__].insert_one(self.mongo())
            if result:
                print("Successfully saved 1 record.")
        except Exception as e:
            print(e)
            raise e

    async def update(self, new_values, field: str = "_id"):
        
        if field != "_id" and not hasattr(self, field):
            raise ValueError(
                f"id field {field} does not exist in type {type(self)}")
        elif field == "_id":
            value = getattr(self, "id")
        else:
            value = getattr(self, field)

        try:
            result = await self.db[self.__collection__].update_one(
                {field: value}, {"$set": new_values})
            if result.modified_count and result.raw_result['updatedExisting']:
                print("Successfully updated 1 record.")
            else:
                print("update failed.")
        except Exception as e:
            print(e)
            raise e

    async def delete(self, field: str = "_id", **kwargs) -> None:
        if field != "_id" and not hasattr(self, field):
            raise ValueError(
                f"id field {field} does not exist in type {type(self)}")
        elif field == "_id":
            value = getattr(self, "id")
        else:
            value = getattr(self, field)

        try:
            result = await self.db[self.__collection__].delete_one(
                {field: value})
            if result:
                print("Successfully deleted 1 record.")
        except Exception as e:
            print(e)
            raise e

if __name__ == "__main__":
    general_mongo_model = MongoModel()
    print(dir(general_mongo_model))
