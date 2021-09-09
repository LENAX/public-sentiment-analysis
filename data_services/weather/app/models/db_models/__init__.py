from .cma_weather import CMAWeatherReportDBModel
from .weather_history import WeatherHistoryDBModel
from .air_quality import AirQualityDBModel

def bind_db_to_all_models(db_client, db_name: str) -> None:
    db = db_client[db_name]
    CMAWeatherReportDBModel.db = db
    WeatherHistoryDBModel.db = db
    AirQualityDBModel.db = db
    
    
    
