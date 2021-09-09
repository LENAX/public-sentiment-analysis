from .db_model import DBModel
from ..data_models import AirQuality as AirQualityDataModel
from typing import Optional, List, Any
from datetime import date, datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson.objectid import ObjectId
from ..extended_types import PydanticObjectId
from pydantic import Field
from uuid import UUID, uuid5, NAMESPACE_OID


class AirQualityDBModel(DBModel, AirQualityDataModel):
    __collection__: str = "AirQuality"
    
    air_quality_id: UUID = Field(
        default_factory=lambda: uuid5(
            NAMESPACE_OID, f"AQ_Object_{datetime.now().timestamp()}"))
