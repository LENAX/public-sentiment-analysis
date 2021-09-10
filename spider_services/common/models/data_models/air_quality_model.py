from pydantic import BaseModel, validator
from typing import Optional
from uuid import UUID
from datetime import date
import numpy as np
# from ..db_models import AirQuality as AirQualityDBModel


class Location(BaseModel):
    locationId: Optional[str]
    areaCode: Optional[str]
    country: Optional[str]
    province: Optional[str]
    city: Optional[str]
    administrativeDivision: Optional[int]


class AirQuality(BaseModel):
    """ Defines an air quality record
  
    """
    province: Optional[str]
    city: Optional[str]
    date: Optional[date]
    quality: Optional[str]
    aqi: Optional[int]
    aqi_rank: Optional[int]
    pm25: Optional[float]
    pm10: Optional[float]
    so2: Optional[float]
    no2: Optional[float]
    co: Optional[float]
    o3: Optional[float]
    lastUpdate: Optional[str]
    
    @validator("pm25", pre=True)
    def validate_pm25(cls, value):
        if type(value) is str and len(value) == 0:
            return np.nan
        elif type(value) is str and value.isdigit():
            return float(value)
        else:
            return value
        
    @validator("pm10", pre=True)
    def validate_pm10(cls, value):
        if type(value) is str and len(value) == 0:
            return np.nan
        elif type(value) is str and value.isdigit():
            return float(value)
        else:
            return value


    def __hash__(self):
        return hash(self.__repr__())

    @classmethod
    def from_db_model(cls, model_instance) -> "AirQuality":
        return cls.parse_obj(model_instance)

    def to_db_model(self) -> "AirQuality":
        pass
