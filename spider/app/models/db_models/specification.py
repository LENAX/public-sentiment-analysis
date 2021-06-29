from .mongo_model import MongoModel
from typing import Optional, List, Any
from datetime import datetime
from ..request_models import ScrapeRules
from ...enums import JobState, ContentType, JobType
from uuid import UUID
from motor.motor_asyncio import AsyncIOMotorDatabase
from uuid import UUID, uuid5, NAMESPACE_OID
from bson.objectid import ObjectId
from ..extended_types import PydanticObjectId
from pydantic import Field


class Specification(MongoModel):
    __collection__: str = "Specification"
    __db__: AsyncIOMotorDatabase = None
    
    id: PydanticObjectId = Field(
        default_factory=lambda: ObjectId())
    specification_id: UUID = Field(
        default_factory=lambda: uuid5(
            NAMESPACE_OID, f"Weather_Object_{datetime.now().timestamp()}"))

    urls: List[str]
    job_type: JobType
    scrape_rules: ScrapeRules
    description: str = Field("")
    create_dt: datetime = Field(default_factory=lambda: datetime.now())
    last_update: datetime = Field(default_factory=lambda: datetime.now())
    remark: str
    
    def __hash__(self):
        return hash(self.__repr__())


