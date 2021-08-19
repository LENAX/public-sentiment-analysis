from dependency_injector import containers, providers

from ..service import (
    WeatherSpiderService,
    BaiduCOVIDSpider,
    DXYCovidReportSpiderService,
    BaiduNewsSpider,
    SpiderFactory,
    WeatherService,
    AirQualityService,
    AsyncJobService,
    SpecificationService,
    NewsService,
    BaiduCOVIDReportService,
    DXYCOVIDReportService
)
from ..models.db_models import (
    Weather, AirQuality, News, BaiduCOVIDReport, PHESCOVIDReport
)
from ..models.data_models import PHESCOVIDReportData
from ..core import (
    RequestClient,
    AsyncBrowserRequestClient,
    Spider,
    ParserContextFactory,
    CrawlerContextFactory
)
from ..db.client import create_client
from .resource_container import ResourceContainer
from .scheduler_container import SchedulerContainer
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.mongodb import MongoDBJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor
from pytz import utc


async def make_request_client(headers, cookies):
    client = await RequestClient(headers=headers, cookies=cookies)
    yield client
    await client.close()


async def make_browser_request_client(headers, cookies):
    client = await AsyncBrowserRequestClient(
        headers=headers, cookies=[cookies])
    yield client
    await client.close()
    
def make_db_client(db_config):
    client = create_client(
        host=db_config['host'],
        port=db_config['port'],
        username=db_config['username'],
        password=db_config['password'],
        db_name=db_config['db_name'])
    yield client
    client.close()
    

def create_scheduler(db_client):
    jobstores = {
        'default': MongoDBJobStore(client=db_client.delegate)
    }
    executors = {
        'default': AsyncIOExecutor()
    }
    job_defaults = {
        'coalesce': False,
        'max_instances': 3
    }
    return AsyncIOScheduler(
        jobstores=jobstores, executors=executors,
        job_defaults=job_defaults, timezone=utc
    )
    

class DataServiceContainer(containers.DeclarativeContainer):
    config = providers.Configuration()
    
    # data services
    weather_service = providers.Singleton(WeatherService)
    aqi_service = providers.Singleton(AirQualityService)
    spec_service = providers.Singleton(SpecificationService)
    news_service = providers.Singleton(NewsService)
    baidu_covid_report_service = providers.Singleton(BaiduCOVIDReportService)
    dxy_covid_report_service = providers.Singleton(DXYCOVIDReportService)
    

class SpiderServiceContainer(containers.DeclarativeContainer):
    config = providers.Configuration()
    resources = providers.DependenciesContainer()
    
    weather_spider_service = providers.Singleton(
        WeatherSpiderService,
        request_client=resources.http_request_client,
        spider_class=Spider,
        parse_strategy_factory=ParserContextFactory,
        crawling_strategy_factory=CrawlerContextFactory,
        result_db_model=Weather
    )
    air_quality_spider_service = providers.Singleton(WeatherSpiderService,
        request_client=resources.http_request_client,
        spider_class=Spider,
        parse_strategy_factory=ParserContextFactory,
        crawling_strategy_factory=CrawlerContextFactory,
        result_db_model=AirQuality
    )
    baidu_covid_spider_service = providers.Singleton(
        BaiduCOVIDSpider,
        request_client=resources.browser_client,
        spider_class=Spider,
        parse_strategy_factory=ParserContextFactory,
        result_db_model=BaiduCOVIDReport
    )
    baidu_news_spider_service = providers.Singleton(
        BaiduNewsSpider,
        request_client=resources.http_request_client,
        spider_class=Spider,
        parse_strategy_factory=ParserContextFactory,
        result_db_model=News
    )
    dxy_covid_spider_service = providers.Singleton(
        DXYCovidReportSpiderService,
        request_client=resources.browser_client,
        result_db_model=PHESCOVIDReport,
        result_data_model=PHESCOVIDReportData
    )

class SpiderDispatcherContainer(containers.DeclarativeContainer):
    config = providers.Configuration()
    resources = providers.DependenciesContainer()
    
    spider_services_container = providers.DependenciesContainer()
    # spider_services_container = providers.Container(
    #     SpiderServiceContainer,
    #     resources=resources
    # )
    
    spider_service_dispatcher = providers.Factory(
        SpiderFactory,
        spider_services=providers.Dict(
            baidu_covid_report=spider_services_container.baidu_covid_spider_service,
            baidu_news_scraping=spider_services_container.baidu_news_spider_service,
            dxy_covid_spider=spider_services_container.dxy_covid_spider_service,
            weather_report=spider_services_container.weather_spider_service
        )
    )
    
    
class Services(containers.DeclarativeContainer):
    """ Declares dependencies for all service modules
    """

    config = providers.Configuration()
    resources = providers.DependenciesContainer()
    scheduler_container = providers.DependenciesContainer()

    data_services_container = providers.Container(
        DataServiceContainer
    )
    spider_services_container = providers.Container(
        SpiderServiceContainer,
        resources=resources
    )
    spider_dispatcher_container = providers.Container(
        SpiderDispatcherContainer,
        spider_services_container=spider_services_container
    )

    # job scheduling service
    job_service = providers.Singleton(
        AsyncJobService,
        async_scheduler=scheduler_container.scheduler
    )


if __name__ == '__main__':
    import asyncio
    from ..config import config as app_config
    from devtools import debug
    
    
    service_container = Services()
    debug(app_config)
    service_container.config.from_dict(app_config)

    async def main(container: containers.Container):
        # http_request_client = await container.http_request_client()
        # browser_client = await container.browser_client()
        weather_spider_service = await container.spider_services_container.weather_spider_service()
        baidu_covid_spider_service = await container.spider_services_container.baidu_covid_spider_service()
        dxy_covid_spider_service = await container.spider_services_container.dxy_covid_spider_service()
        baidu_news_spider_service = await container.spider_services_container.baidu_news_spider_service()
        aqi_spider_service = await container.spider_services_container.air_quality_spider_service()
        job_service = container.job_service()
        aqi_service = container.data_services_container.aqi_service()
        spec_service = container.data_services_container.spec_service()
        news_service = container.data_services_container.news_service()
        baidu_covid_report_service = container.data_services_container.baidu_covid_report_service()
        dxy_covid_report_service = container.data_services_container.dxy_covid_report_service()
        spider_dispatcher_service = await container.spider_dispatcher_container.spider_service_dispatcher()
        
        await asyncio.sleep(3)
        
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(service_container))
    service_container.shutdown_resources()


