from dependency_injector import containers, providers

from ..core import (
    RequestClient,
    AsyncBrowserRequestClient,
    Spider,
    ParserContextFactory,
    CrawlerContextFactory
)
from ..db.client import create_client


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

