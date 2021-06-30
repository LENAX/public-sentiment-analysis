from .mongo_model import MongoModel
from typing import Optional, List, Any, Union
from datetime import date, datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson.objectid import ObjectId
from ..extended_types import PydanticObjectId
from pydantic import Field, validator
from uuid import UUID, uuid5, NAMESPACE_OID
from dateutil import parser
import re

cn_dt_pattern = re.compile(r"\d+年\d+月\d+日")

class Weather(MongoModel):
    __collection__: str = "Weather"
    __db__: AsyncIOMotorDatabase

    id: PydanticObjectId = Field(
        default_factory=lambda: ObjectId())
    weather_id: UUID = Field(
        default_factory=lambda: uuid5(
            NAMESPACE_OID, f"Weather_Object_{datetime.now().timestamp()}"))
    
    title: str = ""
    province: str = ""
    city: str = ""
    date: Optional[Union[date, datetime, str]]
    weather: str = ""
    temperature: str = ""
    wind: str = ""

    remark: str = ""
    create_dt: datetime= Field(
        default_factory=lambda:datetime.now())
    job_id: Optional[UUID]
    user_id: Optional[UUID]
    project_id: Optional[UUID]
    tenant_id: Optional[UUID]

    @validator("date", pre=True)
    def parse_date(cls, value):
        try:
            if value is None or len(value) == 0:
                return None
            elif cn_dt_pattern.match(value):
                year, month, day = [int(x)
                                    for x in re.findall(r"\d+", value)]
                return datetime(year, month, day)
            else:
                return parser.parse(value)
        except IndexError:
            print(f"Parsing datetime failed. value={value}")
            return datetime.now()
