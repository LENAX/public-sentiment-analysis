from .mongo_model import MongoModel
from typing import Optional, List, Any
from datetime import date, datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson.objectid import ObjectId
from ..extended_types import PydanticObjectId
from pydantic import Field, validator
from uuid import UUID, uuid5, NAMESPACE_OID
from dateutil import parser


class News(MongoModel):
    __collection__: str = "News"
    __db__: AsyncIOMotorDatabase

    id: PydanticObjectId = Field(
        default_factory=lambda: ObjectId())
    news_id: UUID = Field(
        default_factory=lambda: uuid5(
            NAMESPACE_OID, f"News_Object_{datetime.now().timestamp()}"))
    
    url: str = ""
    title: str = ""
    author: str = ""
    publish_time: datetime
    content: str = ""
    images: List[str] = []
    
    remark: str = ""
    job_id: Optional[UUID]
    user_id: Optional[UUID]
    project_id: Optional[UUID]
    tenant_id: Optional[UUID]

    @validator("publish_time", pre=True)
    def parse_publish_time(cls, value):
        try:
            return parser.parse(value)
        except IndexError:
            print(f"Parsing datetime failed. value={value}")
            return datetime.now()
