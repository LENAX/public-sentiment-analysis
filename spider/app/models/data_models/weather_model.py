from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import  date
from ..db_models import Weather as WeatherDBModel


class WeatherData(BaseModel):
    """ Defines a weather record
    
    Fields:
        field_name: Optional[str],
        field_value: Optional[str]  
    """
    weather_id: Optional[UUID]
    title: Optional[str] = ""
    province: Optional[str] = ""
    city: Optional[str] = ""
    date: Optional[date]
    weather: Optional[str] = ""
    temperature: Optional[str] = ""
    wind: Optional[str] = ""


    def __hash__(self):
        return hash(self.__repr__())

    @classmethod
    def from_db_model(cls, model_instance: WeatherDBModel) -> "WeatherData":
        return cls.parse_obj(model_instance)

    def to_db_model(self) -> WeatherDBModel:
        pass
