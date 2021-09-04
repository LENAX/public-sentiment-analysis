from dependency_injector import containers, providers
from ...common.db.client import create_client
from ...common.core import (
    RequestClient,
    AsyncBrowserRequestClient,
    ParserContextFactory,
    CrawlerContextFactory,
    Spider
)
from ...common.models.db_models import WeatherReportDBModel
from ...common.models.data_models import WeatherReport

from .service import WeatherForecastSpiderService

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
    

class ResourceContainer(containers.DeclarativeContainer):
    config = providers.Configuration()

    # required resources for services
    db_client = providers.Resource(
        make_db_client,
        db_config=config
    )
    http_request_client = providers.Resource(
        make_request_client,
        headers=config.headers,
        cookies=config.cookies
    )
    browser_client = providers.Resource(
        make_browser_request_client,
        headers=config.headers,
        cookies=config.cookies
    )


class ServiceContainer(containers.DeclarativeContainer):
    config = providers.Configuration()
    resources = providers.DependenciesContainer()

    weather_forecast_spider_service = providers.Singleton(
        WeatherForecastSpiderService,
        request_client=resources.browser_client,
        spider_class=Spider,
        parse_strategy_factory=ParserContextFactory,
        crawling_strategy_factory=CrawlerContextFactory,
        result_db_model=WeatherReportDBModel,
        result_data_model=WeatherReport
    )

class Application(containers.DeclarativeContainer):
    """Application dependency container

    Containers:
        resources, 
        scheduler, 
        services
    """

    config = providers.Configuration()

    resources = providers.Container(
        ResourceContainer,
        config=config.db,
    )
