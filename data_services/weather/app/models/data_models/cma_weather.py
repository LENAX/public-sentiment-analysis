from pydantic import BaseModel
from typing import Optional
import ujson

class Location(BaseModel):
    locationId: Optional[str]
    areaCode: Optional[str]
    country: Optional[str]
    province: Optional[str]
    city: Optional[str]
    administrativeDivision: Optional[int]


class CMAWeatherReport(BaseModel):
    temperature: Optional[float]
    pressure: Optional[float]
    humidity: Optional[float]
    precipitation: Optional[float]
    windDirection: Optional[str]
    windDirectionDegree: Optional[int]
    windScale: Optional[str]
    windSpeed: Optional[float]
    location: Optional[Location]
    lastUpdate: Optional[str]
    
    class Config:
        json_loads = ujson.loads
        json_dumps = ujson.dumps

    @classmethod
    def from_db_model(cls, model_instance) -> "CMAWeatherReport":
        return cls.parse_obj(model_instance)
    
    
