from dependency_injector import containers, providers
from ...common.db.client import create_client
from ...common.core import (
    RequestClient,
    AsyncBrowserRequestClient,
    ParserContextFactory,
    CrawlerContextFactory,
    Spider
)
from ...common.models.db_models import AirQualityDBModel

from .service import AQISpiderService

async def make_request_client(headers, cookies):
    # client = await RequestClient(headers=headers, cookies=cookies)
    # yield client
    async with (await RequestClient(headers=headers, cookies=cookies)) as client:
        yield client
    # await client.close()


async def make_browser_request_client(headers, cookies):
    async with (await AsyncBrowserRequestClient(headers=headers, cookies=[cookies])) as client:
        yield client


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
    aqi_spider_service = providers.Singleton(
        AQISpiderService,
        request_client=resources.http_request_client,
        spider_class=Spider,
        parse_strategy_factory=ParserContextFactory,
        crawling_strategy_factory=CrawlerContextFactory,
        result_db_model=AirQualityDBModel)



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
    
    services = providers.Container(
        ServiceContainer,
        config=config,
        resources=resources)
