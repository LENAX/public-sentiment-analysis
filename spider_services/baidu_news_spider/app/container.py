from spider_services.baidu_news_spider.app.rpc.models import ArticleSummary, ArticlePopularity
from dependency_injector import containers, providers
from spider_services.common.models.data_models.news import News
from spider_services.common.models.db_models.news import NewsDBModel

from ...common.core import AsyncBrowserRequestClient, RequestClient, Spider
from ...common.db.client import create_client
from .service import BaiduNewsSpiderService


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


class RPCServiceContainer(containers.DeclarativeContainer):
    config = providers.Configuration()
    resources = providers.DependenciesContainer()
    
    article_summary_service = providers.Singleton(
        remote_service_endpoint=config.article_summary_service,
        request_client=resources.http_request_client,
        response_model=ArticleSummary
    )
    
    article_popularity_service = providers.Singleton(
        remote_service_endpoint=config.article_popularity_service,
        request_client=resources.http_request_client,
        response_model=ArticlePopularity
    )
    
    article_classification_service = providers.Singleton(
        remote_service_endpoint=config.article_classification_service,
        request_client=resources.http_request_client
    )

class ServiceContainer(containers.DeclarativeContainer):
    config = providers.Configuration()
    resources = providers.DependenciesContainer()
    rpc_services = providers.DependenciesContainer()

    baidu_news_spider_service = providers.Singleton(
        BaiduNewsSpiderService,
        request_client=resources.http_request_client,
        spider_class=Spider,
        result_db_model=News,
        result_data_model=NewsDBModel
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
        resources=resources,
        config=config)
