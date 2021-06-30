""" Application level dependency container
"""

from dependency_injector.wiring import inject, Provide
from dependency_injector import containers, providers

from .service_containers import Services
from .resource_container import ResourceContainer
from .scheduler_container import SchedulerContainer

class Application(containers.DeclarativeContainer):

    config = providers.Configuration()

    resources = providers.Container(
        ResourceContainer,
        config=config.db,
    )

    scheduler = providers.Container(
        SchedulerContainer,
        resources=resources
    )

    services = providers.Container(
        Services,
        resources=resources,
        scheduler_container=scheduler
    )

