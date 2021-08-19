from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from devtools import debug


class DXYCityCOVIDReport(BaseModel):
    cityName: str
    currentConfirmedCount: int
    currentConfirmedCountStr: Optional[str]
    confirmedCount: int
    suspectedCount: int
    curedCount: int
    deadCount: int
    highDangerCount: int
    midDangerCount: int
    locationId: int
    
    
class DangerArea(BaseModel):
    cityName: str
    areaName: str
    dangerLevel: int

class DXYCOVIDReportData(BaseModel):
    provinceName: Optional[str]
    provinceShortName: Optional[str]
    currentConfirmedCount: int
    currentConfirmedIncr: Optional[int]
    confirmedCount: int
    confirmedIncr: Optional[int]
    suspectedCount: int
    suspectedCountIncr: Optional[int]
    curedCount: int
    curedIncr: Optional[int]
    dateId: Optional[int]
    deadCount: int
    deadIncr: Optional[int]
    comment: Optional[str]
    locationId: Optional[int]
    statisticsData: Optional[str]
    highDangerCount: int
    midDangerCount: int
    detectOrgCount: Optional[int]
    vaccinationOrgCount: Optional[int]
    cities: Optional[List[DXYCityCOVIDReport]]
    dangerAreas: Optional[List[DangerArea]]
