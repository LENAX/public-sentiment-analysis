from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from ..db_models import BaiduCOVIDReport as COVIDReportDBModel
from devtools import debug

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

    def __hash__(self):
        return hash(self.__repr__())

    @classmethod
    def from_db_model(cls, model_instance: COVIDReportDBModel) -> "COVIDReportData":
        debug(model_instance)
        return cls.parse_obj(model_instance)

    def to_db_model(self) -> COVIDReportDBModel:
        pass
