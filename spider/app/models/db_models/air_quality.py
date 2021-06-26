from .mongo_model import MongoModel
from typing import Optional, List, Any
from datetime import date, datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson.objectid import ObjectId
from ..extended_types import PydanticObjectId
from pydantic import Field
from uuid import UUID, uuid5, NAMESPACE_OID

class AirQuality(MongoModel):
    __collection__: str = "AirQuality"
    __db__: AsyncIOMotorDatabase

    id: PydanticObjectId = Field(
        default_factory=lambda: ObjectId())
    air_quality: UUID = Field(
        default_factory=lambda: uuid5(
            NAMESPACE_OID, f"AQ_Object_{datetime.now().timestamp()}"))

    title: str = ""
    province: str = ""
    city: str = ""
    date: date
    quality: str = ""
    AQI: str = ""
    AQI_rank: str = ""
    PM25: str = ""
    PM10: str = ""
    SO2: str = ""
    NO2: str = ""
    Co: str = ""
    O3: str = ""
    
    remark: str = ""
    create_dt: Optional[datetime]
    job_id: Optional[UUID]
    user_id: Optional[UUID]
    project_id: Optional[UUID]
    tenant_id: Optional[UUID]
