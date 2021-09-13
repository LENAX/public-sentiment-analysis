from pydantic import BaseModel
from typing import Optional


class CMADailyWeather(BaseModel):
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
    lastUpdate: Optional[str]

    areaCode: Optional[str]
    province: Optional[str]
    city: Optional[str]
