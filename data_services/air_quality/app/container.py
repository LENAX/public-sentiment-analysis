""" Application level dependency container
"""

from .models.db_models import SubscriptionDBModel
from .models.data_models import Subscription as SubscriptionData

from dependency_injector.wiring import inject, Provide
from dependency_injector import containers, providers
from .db import create_client
from .services import (
    HappyPAICNotificationService,
    SubscriptionService
)


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

    happy_paic_notification_service = providers.Singleton(
        HappyPAICNotificationService,
        happy_paic_server_url=config.rpc.happy_paic_server_url)
    subscription_service = providers.Singleton(
        SubscriptionService,
        subscription_data_model=SubscriptionData,
        subscription_db_model=SubscriptionDBModel)


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
