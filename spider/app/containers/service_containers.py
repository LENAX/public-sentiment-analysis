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
from ..models.db_models import (
    Weather, AirQuality, News, COVIDReport
)
from ..core import (
    RequestClient,
    AsyncBrowserRequestClient,
    Spider,
    ParserContextFactory,
    CrawlerContextFactory
)
from ..db.client import create_client

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


class Services(containers.DeclarativeContainer):
    """ Declares dependencies for all service modules
    """

    config = providers.Configuration()
    resources = providers.DependenciesContainer()
    scheduler_container = providers.DependenciesContainer()

    # job scheduling service
    job_service = providers.Singleton(
        AsyncJobService,
        async_scheduler=scheduler_container.scheduler
    )
    
    # data services
    weather_service = providers.Singleton(WeatherService)
    aqi_service = providers.Singleton(AirQualityService)
    spec_service = providers.Singleton(SpecificationService)
    news_service = providers.Singleton(NewsService)
    covid_report_service = providers.Singleton(COVIDReportService)


class SpiderServices(containers.DeclarativeContainer):
    config = providers.Configuration()
    resources = providers.DependenciesContainer()
    
    spider_service_dispatcher = providers.Factory(
        SpiderFactory,
        spider_services=providers.Dict(
            basic_page_scraping=providers.Singleton(
                WeatherSpiderService,
                request_client=resources.http_request_client,
                spider_class=Spider,
                parse_strategy_factory=ParserContextFactory,
                crawling_strategy_factory=CrawlerContextFactory,
                result_db_model=Weather
            ),
            baidu_news_scraping=providers.Singleton(
                BaiduCOVIDSpider,
                request_client=resources.browser_client,
                spider_class=Spider,
                parse_strategy_factory=ParserContextFactory,
                result_db_model=COVIDReport
            ),
            baidu_covid_report=providers.Singleton(
                BaiduNewsSpider,
                request_client=resources.http_request_client,
                spider_class=Spider,
                parse_strategy_factory=ParserContextFactory,
                result_db_model=News
            ),
            weather_report=providers.Singleton(
                WeatherSpiderService,
                request_client=resources.http_request_client,
                spider_class=Spider,
                parse_strategy_factory=ParserContextFactory,
                crawling_strategy_factory=CrawlerContextFactory,
                result_db_model=AirQuality
            )
        )
    )

    # weather_spider_service = providers.Singleton(
    #     WeatherSpiderService,
    #     request_client=resources.http_request_client,
    #     spider_class=Spider,
    #     parse_strategy_factory=ParserContextFactory,
    #     crawling_strategy_factory=CrawlerContextFactory,
    #     result_db_model=Weather
    # )
    # covid_spider_service = providers.Singleton(
    #     BaiduCOVIDSpider,
    #     request_client=resources.browser_client,
    #     spider_class=Spider,
    #     parse_strategy_factory=ParserContextFactory,
    #     result_db_model=COVIDReport
    # )
    # news_spider_service = providers.Singleton(
    #     BaiduNewsSpider,
    #     request_client=resources.http_request_client,
    #     spider_class=Spider,
    #     parse_strategy_factory=ParserContextFactory,
    #     result_db_model=News
    # )
    # aqi_spider_service = providers.Singleton(
    #     WeatherSpiderService,
    #     request_client=resources.http_request_client,
    #     spider_class=Spider,
    #     parse_strategy_factory=ParserContextFactory,
    #     crawling_strategy_factory=CrawlerContextFactory,
    #     result_db_model=AirQuality
    # )

if __name__ == '__main__':
    import asyncio
    from ..config import config as app_config
    from devtools import debug
    
    service_container = Services()
    debug(app_config)
    service_container.config.from_dict(app_config)
    # service_container.init_resources()

    async def main(container: containers.Container):
        db_client = container.db_client()
        # http_request_client = await container.http_request_client()
        # browser_client = await container.browser_client()
        weather_spider_service = await container.weather_spider_service()
        covid_spider_service = await container.covid_spider_service()
        news_spider_service = await container.news_spider_service()
        aqi_spider_service = await container.aqi_spider_service()
        job_service = container.job_service()
        aqi_service = container.aqi_service()
        spec_service = container.spec_service()
        news_service = container.news_service()
        covid_report_service = container.covid_report_service()
        
        await asyncio.sleep(3)
        
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(service_container))
    service_container.shutdown_resources()


