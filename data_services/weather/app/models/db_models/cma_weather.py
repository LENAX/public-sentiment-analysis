from ..data_models import CMAWeatherReport
from .db_model import DBModel
from uuid import UUID, uuid5, NAMESPACE_OID
from datetime import datetime
from typing import Optional
from pydantic import Field
import ujson


class CMAWeatherReportDBModel(DBModel, CMAWeatherReport):
    __collection__: str = "CMAWeatherReport"
    weather_id: Optional[UUID] = Field(default_factory=lambda: uuid5(
        NAMESPACE_OID, f"Weather_{datetime.now().timestamp()}"))
    
    class Config:
        json_loads = ujson.loads
        json_dumps = ujson.dumps
