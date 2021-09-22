from .mongo_model import MongoModel
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson.objectid import ObjectId
from ..extended_types import PydanticObjectId
from pydantic import Field
from uuid import UUID


class DBModel(MongoModel):
    __collection__: str = "Base"
    __db__: AsyncIOMotorDatabase

    id: PydanticObjectId = Field(
        default_factory=lambda: ObjectId())

    remark: str = ""
    job_id: Optional[UUID]
    user_id: Optional[UUID]
    project_id: Optional[UUID]
    tenant_id: Optional[UUID]
    last_update: Optional[str]
