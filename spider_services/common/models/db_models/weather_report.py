from ..data_models import WeatherReport
from .db_model import DBModel


class WeatherReportDBModel(DBModel, WeatherReport):
    __collection__: str = "WeatherReport"
    


