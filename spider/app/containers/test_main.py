""" Test whether DI works
"""
import sys

from dependency_injector.wiring import inject, Provide
from dependency_injector import containers, providers
from .application_container import Application
from devtools import debug


@inject
async def main(spider_service_dispatcher = Provide[
                   Application.services.spider_dispatcher_container.spider_service_dispatcher],
               data_services_container = Provide[
                   Application.services.data_services_container],
               spider_services_container = Provide[
                   Application.services.spider_services_container],
               job_service=Provide[Application.services.job_service],
               weather_spider_service=Provide[Application.services.spider_services_container.weather_spider_service],
               air_quality_spider_service=Provide[Application.services.spider_services_container.air_quality_spider_service],
               baidu_covid_spider_service=Provide[Application.services.spider_services_container.baidu_covid_spider_service],
               baidu_news_spider_service=Provide[Application.services.spider_services_container.baidu_news_spider_service],
               dxy_covid_spider_service=Provide[Application.services.spider_services_container.dxy_covid_spider_service]):
    debug(spider_service_dispatcher)
    debug(data_services_container)
    debug(spider_services_container)
    debug(job_service)
    debug(weather_spider_service)
    debug(air_quality_spider_service)
    debug(baidu_covid_spider_service)
    debug(baidu_news_spider_service)
    debug(dxy_covid_spider_service)

    await asyncio.sleep(3)

if __name__ == '__main__':
    import asyncio
    from ..config import config as app_config
    from devtools import debug

    application = Application()
    debug(app_config)
    application.config.from_dict(app_config)
    application.resources.init_resources()
    application.wire(modules=[sys.modules[__name__]])

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    application.resources.shutdown_resources()
    






