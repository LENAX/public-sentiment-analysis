""" This module contains domain models used and returned by core components and services.
"""

from .data_models import (
    DataModel,
    RequestHeader
)
from .spider_models import HTMLData, URL
from .parser_models import ParseResult
from .crawler_models import CrawlResult
from .job_models import JobData
from .weather_model import WeatherData
from .air_quality_model import AirQualityData
from .news_model import NewsData
from .covid_report_model import COVIDReportData
from .specification_model import SpecificationData
from .schedule_model import Schedule
from .job_status_model import JobStatus
from .dxy_covid_report_model import DXYCOVIDReportData
from .phes_covid_report_model import COVIDReportData as PHESCOVIDReportData
