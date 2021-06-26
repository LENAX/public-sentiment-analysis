from .mongo_model import MongoModel
from typing import Optional, List, Any
from datetime import date, datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson.objectid import ObjectId
from ..extended_types import PydanticObjectId
from pydantic import Field, validator
from uuid import UUID, uuid5, NAMESPACE_OID
from re import findall


class COVIDReport(MongoModel):
    __collection__: str = "COVIDReport"
    __db__: AsyncIOMotorDatabase

    id: PydanticObjectId = Field(
        default_factory=lambda: ObjectId())
    covid_report: UUID = Field(
        default_factory=lambda: uuid5(NAMESPACE_OID, f"News_Object_{datetime.now().timestamp()}"))
    
    report_type: str = ""
    country: Optional[str] = ""
    last_update: datetime = Field(...)
    
    confirmed_cases: str = ""
    new_asymptomatic_cases: str = ""
    suspicious_cases: str = ""
    serious_symptom_cases: str = ""
    domestic_new_cases: str = ""
    imported_cases: str = ""
    
    total_deaths: str = ""
    total_cured: str = ""
    total_cases: str = ""
    total_confirmed_cases: str = ""
    
    mortality_rate: str = ""
    recovery_rate: str = ""

    remark: str = ""
    create_dt: datetime = Field(default_factory=lambda: datetime.now())
    job_id: Optional[UUID]
    user_id: Optional[UUID]
    project_id: Optional[UUID]
    tenant_id: Optional[UUID]

    @validator("last_update", pre=True)
    def parse_last_update(cls, value):
        try:
            dt_str = findall("\d{4}.\d{2}.\d{2}.\d{2}:\d{2}", value)[0]
            return datetime.strptime(
                dt_str,
                "%Y.%m.%d %H:%M"
            )
        except IndexError:
            print(f"Parsing datetime failed. value={value}")
            return datetime.now()
