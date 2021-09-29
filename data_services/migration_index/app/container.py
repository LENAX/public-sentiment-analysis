""" Application level dependency container
"""

from .models.db_models import MigrationRankDBModel, MigrationIndexDBModel
from .models.data_models import MigrationIndex, MigrationRank

from dependency_injector import containers, providers
from .db import create_client
from .services import MigrationIndexReportService, MigrationRankReportService


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


class ServiceContainer(containers.DeclarativeContainer):
    config = providers.Configuration()

    migration_index_report_service = providers.Singleton(
        MigrationIndexReportService,
        data_model=MigrationIndex,
        db_model=MigrationIndexDBModel)
    
    migration_rank_report_service = providers.Singleton(
        MigrationRankReportService,
        data_model=MigrationRank,
        db_model=MigrationRankDBModel)


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
        config=config)
