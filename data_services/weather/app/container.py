""" Application level dependency container
"""

from .models.db_models import CMAWeatherReportDBModel
from .models.data_models import CMADailyWeather, CMAWeatherReport

from dependency_injector.wiring import inject, Provide
from dependency_injector import containers, providers
from .db import create_client
from .services import CMAWeatherReportService


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

    cma_weather_report_service = providers.Singleton(
        CMAWeatherReportService,
        cma_daily_weather_data_model=CMADailyWeather,
        cma_weather_report_data_model=CMAWeatherReport,
        cma_weather_report_db_model=CMAWeatherReportDBModel)


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
        resource=resources,
        config=config)
