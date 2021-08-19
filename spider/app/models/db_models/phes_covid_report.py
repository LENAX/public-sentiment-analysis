from .mongo_model import MongoModel
from typing import Optional, List, Any, Union
from datetime import date, datetime, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson.objectid import ObjectId
from ..extended_types import PydanticObjectId
from pydantic import Field, validator
from uuid import UUID, uuid5, NAMESPACE_OID
from re import findall
from dateutil import parser


class COVIDReport(MongoModel):
    __collection__: str = "COVIDReport"
    __db__: AsyncIOMotorDatabase

    id: PydanticObjectId = Field(
        default_factory=lambda: ObjectId())
    covid_report_id: Union[UUID, str] = Field(
        default_factory=lambda: str(uuid5(NAMESPACE_OID, f"COVID_Report_{datetime.now().timestamp()}")))
    
    province: Optional[str]
    city: Optional[str]
    areaCode: Optional[str]
    localNowExisted: Optional[float]
    localIncreased: Optional[float]
    otherHasIncreased: Optional[int]
    localNowReported: Optional[float]
    localNowReportedIncrease: Optional[float]
    localNowCured: Optional[float]
    localNowCuredIncrease: Optional[float]
    localNowDeath: Optional[float]
    localDeathIncrease: Optional[float]
    foreignNowReported: Optional[float]
    importedCuredCases: Optional[float]
    importedcuredCasesIncrease: Optional[float]
    importedNowExisted: Optional[float]
    foreignEnterIncrease: Optional[float]
    foreignEnterIncrease: Optional[float]
    foreignNowDeath: Optional[float]
    foreignNowDeathIncrease: Optional[float]
    suspectCount: Optional[float]
    suspectIncrease: Optional[float]
    highDangerZoneCount: Optional[float]
    midDangerZoneCount: Optional[float]
    isImportedCase: Optional[bool]
    lastUpdate: str = Field(default_factory=lambda: datetime.now().replace(
        microsecond=0).strftime("%Y-%m-%d 00:00:00"))
    recordDate: str = Field(default_factory=lambda: datetime.now(
    ).replace(microsecond=0).strftime("%Y-%m-%d 00:00:00"))

    remark: str = ""
    create_dt: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    job_id: Optional[UUID]
    user_id: Optional[UUID]
    project_id: Optional[UUID]
    tenant_id: Optional[UUID]

    @validator("lastUpdate", pre=True)
    def parse_last_update(cls, value):
        try:
            if type(value) is datetime:
                return value.strftime("%Y-%m-%dT%H:%M:%S")
            return parser.parse(value).strftime("%Y-%m-%dT%H:%M:%S")
        except IndexError:
            print(f"Parsing datetime failed. value={value}")
            return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    
    @validator("recordDate", pre=True)
    def parse_date(cls, value):
        try:
            if type(value) is int:
                return parser.parse(str(value)).strftime("%Y-%m-%dT%H:%M:%S")
            elif type(value) is datetime:
                return value.strftime("%Y-%m-%dT%H:%M:%S")
            
            return parser.parse(value).strftime("%Y-%m-%dT%H:%M:%S")
        except IndexError:
            print(f"Parsing datetime failed. value={value}")
            return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    
    @validator("areaCode", pre=True)
    def parse_location_id(cls, value):
        if type(value) is str:
            return value
        elif type(value) is int:
            return str(value)
        else:
            raise TypeError("Location id should be either a string or an int")
