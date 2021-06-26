from .mongo_model import MongoModel
from typing import Optional, List, Any
from datetime import date, datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson.objectid import ObjectId
from ..extended_types import PydanticObjectId
from pydantic import Field
from uuid import UUID, uuid5, NAMESPACE_OID


class Weather(MongoModel):
    __collection__: str = "AirQuality"
    __db__: AsyncIOMotorDatabase

    id: PydanticObjectId = Field(
        default_factory=lambda: ObjectId())
    weather: UUID = Field(
        default_factory=lambda: uuid5(
            NAMESPACE_OID, f"Weather_Object_{datetime.now().timestamp()}"))
    
    title: str = ""
    province: str = ""
    city: str = ""
    date: date
    weather: str = ""
    temperature: str = ""
    wind: str = ""

    remark: str = ""
    job_id: Optional[UUID]
    user_id: Optional[UUID]
    project_id: Optional[UUID]
    tenant_id: Optional[UUID]
