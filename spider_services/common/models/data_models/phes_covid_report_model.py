from pydantic import BaseModel
from typing import Optional, List, Union
from uuid import UUID
from datetime import datetime
# from ..db_models import PHESCOVIDReport as COVIDReportDBModel
from devtools import debug


class DangerArea(BaseModel):
    areaName: str
    cityName: str
    dangerLevel: int

class COVIDReportData(BaseModel):
    """ Defines a weather record
    
    Fields:
        covid_report_id: Optional[UUID]
        report_type: Optional[str] = ""
        country: Optional[str] = ""
        last_update: Optional[datetime]
        confirmed_cases: Optional[str] = ""
        new_asymptomatic_cases: Optional[str] = ""
        suspicious_cases: Optional[str] = ""
        serious_symptom_cases: Optional[str] = ""
        domestic_new_cases: Optional[str] = ""
        imported_cases: Optional[str] = ""

        total_deaths: Optional[str] = ""
        total_cured: Optional[str] = ""
        total_cases: Optional[str] = ""
        total_confirmed_cases: Optional[str] = ""

        mortality_rate: Optional[str] = ""
        recovery_rate: Optional[str] = ""

        remark: Optional[str] = ""
    """
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
    dangerAreas: Optional[List[DangerArea]]
    highDangerZoneCount: Optional[float]
    midDangerZoneCount: Optional[float]
    isImportedCase: Optional[bool]
    lastUpdate: Optional[Union[str, datetime]]
    recordDate: Optional[Union[str, datetime]]
    create_dt: Optional[Union[str, datetime]]

    def __hash__(self):
        return hash(self.__repr__())

    @classmethod
    def from_db_model(cls, model_instance) -> "COVIDReportData":
        return cls.parse_obj(model_instance)

    def to_db_model(self):
        pass
