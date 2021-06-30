""" Test whether DI works
"""
import sys

from dependency_injector.wiring import inject, Provide
from dependency_injector import containers, providers


from ..service import (
    WeatherSpiderService,
    BaiduCOVIDSpider,
    BaiduNewsSpider,
    SpiderFactory,
    WeatherService,
    AirQualityService,
    AsyncJobService,
    SpecificationService,
    NewsService,
    COVIDReportService
)

from .application_container import Application
from devtools import debug


@inject
async def main(weather_spider_service: WeatherSpiderService = Provide[
                  Application.services.weather_spider_service],
               covid_spider_service: BaiduCOVIDSpider = Provide[
                  Application.services.covid_spider_service],
               news_spider_service: BaiduNewsSpider = Provide[
                   Application.services.news_spider_service],
               aqi_spider_service: WeatherService = Provide[
                   Application.services.aqi_spider_service],
               job_service: AsyncJobService = Provide[
                   Application.services.job_service],
               aqi_service: AirQualityService = Provide[
                   Application.services.aqi_service],
               spec_service: SpecificationService = Provide[
                   Application.services.spec_service],
               news_service: NewsService = Provide[
                   Application.services.news_service],
               covid_report_service: COVIDReportService = Provide[
                   Application.services.covid_report_service]
            ):

    debug(weather_spider_service)
    debug(covid_spider_service)
    debug(news_spider_service)
    debug(aqi_spider_service)
    debug(job_service)
    debug(aqi_service)
    debug(spec_service)
    debug(news_service)
    debug(covid_report_service)

    await asyncio.sleep(3)

if __name__ == '__main__':
    import asyncio
    from ..config import config as app_config
    from devtools import debug

    # service_container = Services()
    # debug(app_config)
    # service_container.config.from_dict(app_config)
    # # service_container.init_resources()


    
    # loop.run_until_complete(main())
    # service_container.shutdown_resources()
    application = Application()
    debug(app_config)
    application.config.from_dict(app_config)
    application.resources.init_resources()
    application.wire(modules=[sys.modules[__name__]])

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(*sys.argv[1:]))
    application.resources.shutdown_resources()
    






