from ..data_models import HistoricalWeatherReport
from .db_model import DBModel
from uuid import UUID, uuid5, NAMESPACE_OID
from datetime import datetime
from typing import Optional
from pydantic import Field


class WeatherHistoryDBModel(DBModel, HistoricalWeatherReport):
    __collection__: str = "WeatherHistory"
    weather_history_id: Optional[UUID] = Field(default_factory=lambda: uuid5(
        NAMESPACE_OID, f"WeatherHistory_{datetime.now().timestamp()}"))
