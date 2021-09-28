from dependency_injector import containers, providers
from ...common.db.client import create_client
from ...common.core import (
    RequestClient,
    AsyncBrowserRequestClient,
    Spider
)
from ...common.models.db_models import MigrationIndexDBModel, MigrationRankDBModel
from ...common.models.data_models import MigrationRank, MigrationIndex

from .service import MigrationRankSpiderService, MigrationIndexSpiderService
from .utils import get_area_code_dict
from os import getcwd

async def make_request_client(headers, cookies):
    async with (await RequestClient(headers=headers, cookies=cookies)) as client:
        yield client


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
    area_code_dict = providers.Object(
        get_area_code_dict(f"{getcwd()}/spider_services/migration_index_spider/app/service_configs/pc-code.json"))
    
    migration_index_spider_service = providers.Singleton(
        MigrationIndexSpiderService,
        request_client=resources.http_request_client,
        spider_class=Spider,
        result_db_model=MigrationIndexDBModel,
        result_data_model=MigrationIndex
    )

    migration_rank_spider_service = providers.Singleton(
        MigrationRankSpiderService,
        request_client=resources.http_request_client,
        spider_class=Spider,
        result_db_model=MigrationRankDBModel,
        result_data_model=MigrationRank,
        area_code_dict=area_code_dict
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
    
    services = providers.Container(
        ServiceContainer,
        resources=resources,
        config=config)
