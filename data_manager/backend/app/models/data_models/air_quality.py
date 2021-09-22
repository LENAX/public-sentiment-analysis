from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import date


class AirQuality(BaseModel):
    """ Defines an air quality record
  
    """
    province: Optional[str]
    city: Optional[str] 
    date: Optional[str]
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
