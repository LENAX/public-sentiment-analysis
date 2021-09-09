from pydantic import BaseModel, Field, validator
from devtools import debug
from dateutil import parser
import re
from datetime import  date, datetime
from uuid import UUID
from typing import Optional, Union, Any
from pydantic import BaseModel
from typing import Optional


cn_dt_pattern = re.compile(r"\d+年\d+月\d+日")

class HistoricalWeatherReport(BaseModel):
    title: Optional[str] = ""
    province: Optional[str] = ""
    city: Optional[str] = ""
    date: Optional[Union[date, datetime, str]]
    weather: Optional[str] = ""
    temperature: Optional[str] = ""
    wind: Optional[str] = ""

    def __hash__(self):
        return hash(self.__repr__())

    @classmethod
    def from_db_model(cls, model_instance) -> "HistoricalWeatherReport":
        return cls.parse_obj(model_instance)

    @validator("date", pre=True)
    def parse_date(cls, value):
        try:
            if type(value) is datetime or type(value) is date:
                return value
            elif value is None or len(value) == 0:
                return None
            elif cn_dt_pattern.match(value):
                year, month, day = [int(x)
                                    for x in re.findall(r"\d+", value)]
                return datetime(year, month, day)
            else:
                return parser.parse(value)
        except IndexError:
            print(f"Parsing datetime failed. value={value}")
            return datetime.now()
