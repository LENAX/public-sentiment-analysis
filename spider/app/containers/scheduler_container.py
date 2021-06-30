from dependency_injector import containers, providers

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.mongodb import MongoDBJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor
from pytz import utc


def create_scheduler(db_client):
    jobstores = {
        'default': MongoDBJobStore(client=db_client.delegate)
    }
    executors = {
        'default': AsyncIOExecutor()
    }
    job_defaults = {
        'coalesce': False,
        'max_instances': 3
    }
    return AsyncIOScheduler(
        jobstores=jobstores, executors=executors,
        job_defaults=job_defaults, timezone=utc
    )


class SchedulerContainer(containers.DeclarativeContainer):
    # config = providers.Configuration()
    resources = providers.DependenciesContainer()
    
    scheduler = providers.Factory(
        create_scheduler,
        resources.db_client)
