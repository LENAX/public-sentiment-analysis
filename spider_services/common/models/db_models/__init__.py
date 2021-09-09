from .html_data import HTMLData
from .job_model import Job
from .specification import Specification
from .result import Result
from .air_quality import AirQualityDBModel
from .covid_report import COVIDReport as BaiduCOVIDReport
from .phes_covid_report import COVIDReport as PHESCOVIDReport
from .news import News
from .weather import Weather
from .weather_report import WeatherReportDBModel
from .cma_weather_report import CMAWeatherReportDBModel



def bind_db_to_all_models(db_client, db_name: str) -> None:
    db = db_client[db_name]
    Job.db = db
    HTMLData.db = db
    Specification.db = db
    Result.db = db
    AirQualityDBModel.db = db
    BaiduCOVIDReport.db = db
    PHESCOVIDReport.db = db
    News.db = db
    Weather.db = db
    WeatherReportDBModel.db = db
    CMAWeatherReportDBModel.db = db
