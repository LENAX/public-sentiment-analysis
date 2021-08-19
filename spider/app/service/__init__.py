from .spider_services import(
    HTMLSpiderService,
    WeatherSpiderService,
    BaiduCOVIDSpider,
    BaiduNewsSpider,
    SpiderFactory
)
from .dxy_spider_service import DXYCovidReportSpiderService
from .weather_services import WeatherService
from .air_quality_services import AirQualityService
from .job_services import AsyncJobService
from .specification_service import SpecificationService
from .news_services import NewsService
from .covid_report_services import COVIDReportService as BaiduCOVIDReportService
from .dxy_covid_report_service import COVIDReportService as DXYCOVIDReportService
