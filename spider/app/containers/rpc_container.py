from dependency_injector import containers, providers
from functools import partial
from ..rpc import run_crawling_task

class RPCContainer(containers.DeclarativeContainer):
    config = providers.Configuration()
    
    spider_rpc = providers.Object(run_crawling_task)

