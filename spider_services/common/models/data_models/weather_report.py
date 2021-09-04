from pydantic import BaseModel, validator, Field
from typing import Optional, Union, Any, List
from uuid import UUID
from datetime import date, datetime
import re
from uuid import UUID, uuid5, NAMESPACE_OID
from dateutil import parser

cn_dt_pattern = re.compile(r"\d+年\d+月\d+日")


class HourlyForecast(BaseModel):
    time: Optional[datetime]
    weather: Optional[str]
    temperature: Optional[float]
    humidity: Optional[float]
    precipitation: Optional[str]
    pressure: Optional[float]
    windSpeed: Optional[float]
    windDirection: Optional[str]
    cloud: Optional[float]
    
    @validator("time", pre=True)
    def parse_time(cls, value):
        try:
            if type(value) is str:
                return parser.parse(value)

            return value
        except Exception as e:
            raise e
        
    @validator("humidity", pre=True)
    def parse_humidity(cls, value):
        try:
            if type(value) is str:
                return float(value)
            elif type(value) is float:
                return value

            return value
        except Exception as e:
            raise e
        
    @validator("cloud", pre=True)
    def parse_cloud(cls, value):
        try:
            if type(value) is str:
                return float(value)
            elif type(value) is float:
                return value

            return value
        except Exception as e:
            raise e
        
    @validator("windSpeed", pre=True)
    def parse_wind_speed(cls, value):
        try:
            if type(value) is str:
                return float(value)
            elif type(value) is float:
                return value

            return value
        except Exception as e:
            raise e
    
    @validator("temperature", pre=True)
    def parse_temperature(cls, value):
        try:
            if type(value) is str:
                return float(value)
            elif type(value) is float:
                return value
            
            return value
        except Exception as e:
            raise e
        
        
            


class TodayForecast(BaseModel):
    highestTemperature: Optional[int]
    morningWeather: Optional[str]
    morningWindDirection: Optional[str]
    morningWindScale: Optional[str]
    lowestTemperature: Optional[int]
    eveningWeather: Optional[str]
    hasWeatherChanged: Optional[int]
    eveningWindDirection: Optional[str]
    eveningWindScale: Optional[str]


class DailyForecast(BaseModel):
    day: Optional[str]
    date: Optional[str]
    today: Optional[TodayForecast]
    hourlyForecast: Optional[List[HourlyForecast]]
    

class WeeklyWeatherForecast(BaseModel):
    data: List[DailyForecast] = []
    last_update: Optional[datetime]
    
    @validator("last_update", pre=True)
    def parse_update_dt(cls, value):
        try:
            if type(value) is str:
                return parser.parse(value)
            
            return value
        except Exception as e:
            raise e


class WeatherNow(BaseModel):
    temperature: Optional[float]
    pressure: Optional[float]
    humidity: Optional[float]
    precipitation: Optional[float]
    windDirection: Optional[str]
    windDirectionDegree: Optional[int]
    windScale: Optional[str]
    windSpeed: Optional[float]


class Location(BaseModel):
    locationId: Optional[str]
    areaCode: Optional[str]
    country: Optional[str]
    province: Optional[str]
    city: Optional[str]
    administrativeDivision: Optional[int]
    

class WeatherAlert(BaseModel):
    effective: Optional[str]
    eventType: Optional[str]
    severity: Optional[str]
    signallevel: Optional[str]
    signaltype: Optional[str]
    title: Optional[str]


class WeatherReport(BaseModel):
    """ Defines a weather record
    
    Fields:

    """
    weather_id: Optional[UUID] = Field(default_factory=lambda: uuid5(
            NAMESPACE_OID, f"Weather_{datetime.now().timestamp()}"))
    location: Optional[Location]
    weatherNow: Optional[WeatherNow]
    todayForecast: Optional[TodayForecast]
    weeklyForecast: Optional[WeeklyWeatherForecast]
    weatherAlerts: Optional[List[WeatherAlert]]
    create_dt: Optional[datetime]
    last_update: Optional[datetime]

    def __hash__(self):
        return hash(self.__repr__())

    @classmethod
    def from_db_model(cls, model_instance) -> "WeatherReport":
        return cls.parse_obj(model_instance)
