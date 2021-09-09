from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class WeatherAQI(BaseModel):
    """ Defines an air quality record
  
    """
    aqi: Optional[int]
    avgAirPressure: Optional[float]
    avgDailyWindSpeed: Optional[float]
    avgRelativeHumidity: Optional[float]
    avgTemperature: Optional[float]
    maxAirPressure: Optional[float]
    maxHumidity: Optional[float]
    maxTemperature: Optional[float]
    minAirPressure: Optional[float]
    minHumidity: Optional[float]
    minTemperature: Optional[float]
    precipitation: Optional[float]
    
    aqi_rank: Optional[int]
    pm25: Optional[float]
    pm10: Optional[float]
    so2: Optional[float]
    no2: Optional[float]
    co: Optional[float]
    o3: Optional[float]
    
    province: Optional[str]
    city: Optional[str]
    areaCode: Optional[str]
    lastUpdate: Optional[datetime]
    
    @classmethod
    def from_db_model(cls, model_instance) -> "WeatherAQI":
        return cls.parse_obj(model_instance)

