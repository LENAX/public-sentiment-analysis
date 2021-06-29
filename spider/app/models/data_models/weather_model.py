from pydantic import BaseModel, Field, validator
from typing import Optional
from uuid import UUID
from datetime import  date, datetime
from ..db_models import Weather as WeatherDBModel
import re
from dateutil import parser

cn_dt_pattern = re.compile("\d+年\d+月\d+日")

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
    create_dt: datetime = Field(
        default_factory=lambda: datetime.now())


    def __hash__(self):
        return hash(self.__repr__())

    @classmethod
    def from_db_model(cls, model_instance: WeatherDBModel) -> "WeatherData":
        return cls.parse_obj(model_instance)

    def to_db_model(self) -> WeatherDBModel:
        pass

    @validator("date", pre=True)
    def parse_publish_time(cls, value):
        try:
            if cn_dt_pattern.match(value):
                year, month, day = [int(x)
                                    for x in re.findall("\d+", value)]
                return datetime(year, month, day)
            else:
                return parser.parse(value)
        except IndexError:
            print(f"Parsing datetime failed. value={value}")
            return datetime.now()
