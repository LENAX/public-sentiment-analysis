""" Application level dependency container
"""

from data_services.news.app.models.data_models.news import News
from data_services.news.app.models.data_models.theme import Theme
from data_services.news.app.models.db_models.news import NewsDBModel
from data_services.news.app.models.db_models.theme import ThemeDBModel
from data_services.news.app.rpc.models import WordCloud as WordCloudResponse
from data_services.news.app.rpc.models import WordCloudRequestArgs
from data_services.news.app.rpc.models.spider_args import BaiduNewsSpiderArgs
from data_services.news.app.rpc.news_spider import NewsSpiderService
from data_services.news.app.rpc.word_cloud_service import \
    WordCloudGenerationService
from dependency_injector import containers, providers

from .db.client import create_client
from .models.data_models import NewsWordCloud, WordCloud
from .rpc.request_client import RequestClient
from .services import NewsService, ThemeService, WordCloudService


def make_db_client(db_config):
    client = create_client(
        host=db_config['host'],
        port=db_config['port'],
        username=db_config['username'],
        password=db_config['password'],
        db_name=db_config['db_name'])
    yield client
    client.close()
    

async def make_request_client(headers, cookies):
    async with (await RequestClient(headers=headers, cookies=cookies)) as client:
        yield client


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
    

class RPCServiceContainer(containers.DeclarativeContainer):
    config = providers.Configuration()
    resources = providers.DependenciesContainer()

    word_cloud_service = providers.Singleton(
        WordCloudGenerationService,
        remote_service_endpoint=config.word_cloud_service,
        request_client=resources.http_request_client,
        request_model=WordCloudRequestArgs,
        response_model=WordCloudResponse,
        word_cloud_model=WordCloud,
    )
    news_spider_service = providers.Singleton(
        NewsSpiderService,
        remote_service_endpoint=config.news_spider_service,
        request_client=resources.http_request_client,
        request_model=BaiduNewsSpiderArgs
    )


class ServiceContainer(containers.DeclarativeContainer):
    config = providers.Configuration()
    rpc_services = providers.DependenciesContainer()

    # NewsService, ThemeService, WordCloudService
    news_service = providers.Singleton(
        NewsService,
        data_model=News,
        db_model=NewsDBModel)
    theme_service = providers.Singleton(
        ThemeService,
        data_model=Theme,
        db_model=ThemeDBModel,
        news_spider_service=rpc_services.news_spider_service)
    word_cloud_service = providers.Singleton(
        WordCloudService,
        data_model=NewsWordCloud,
        news_service=news_service,
        word_cloud_generation_service=rpc_services.word_cloud_service
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
    
    rpc_services = providers.Container(
        RPCServiceContainer,
        resources=resources,
        config=config.rpc
    )
    
    services = providers.Container(
        ServiceContainer,
        config=config,
        rpc_services=rpc_services)
