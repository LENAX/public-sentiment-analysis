from spider.app import db
from typing import List, Any, Callable
from collections.abc import Coroutine
from .base_services import BaseJobService
from apscheduler.schedulers.base import BaseScheduler
from apscheduler.triggers.base import BaseTrigger
from apscheduler.job import Job as APJob
from ..models.response_models import (
    JobResponse
)
from ..models.db_models import JobStatus, Job
from datetime import datetime, timedelta
from ..enums import JobType, JobState
from uuid import uuid4, UUID
from datetime import datetime
from bson.objectid import ObjectId

class AsyncJobService(BaseJobService):
    """ Provides async job management using APScheduler

    """
    def __init__(self,
                 async_scheduler: BaseScheduler,
                 job_model: Job = Job,
                 job_status_model: JobStatus = JobStatus,
                 oid_generator: ObjectId = ObjectId,
                 uuid_generator: Callable = uuid4,
                 datetime: datetime = datetime) -> None:
        self._async_scheduler = async_scheduler
        self._job_model = job_model
        self._job_status_model = job_status_model
        self._oid_generator = oid_generator
        self._uuid_generator = uuid_generator
        self._datetime = datetime

    async def add_job(self, func: Callable,
                  trigger: BaseTrigger = None, name: str = None,
                  description: str = "", misfire_grace_time: int = None,
                  coalesce: bool = False, max_instances: int = 1,
                  next_run_time=None, jobstore: str = 'default',
                  executor: str = 'default', replace_existing: bool = False,
                  **trigger_args) -> JobResponse:
        job_id = self._uuid_generator()
        # might be blocking under the hood...
        # TODO: run in a separate thread to avoid blocking the event loop
        try:
            ap_job = self._async_scheduler.add_job(
                func=func, trigger=trigger, id=str(job_id), name=name
            )
            job = Job(
                id=self._oid_generator(),
                job_id=job_id,
                name=ap_job.name,
                description=description,
                current_state=JobState.WORKING,
                next_run_time=ap_job.next_run_time
            )
            await job.save()
            create_dt = self._datetime.now()
            return JobResponse.success(
                        job_id=str(job_id),
                        job=job,
                        create_dt=create_dt,
                        last_update=create_dt)
        except Exception as e:
            return JobResponse.fail(status_code=500, message=str(e))

    async def update_job(self, job_id: str, **changes) -> JobResponse:
        try:
            ap_job = self._async_scheduler.get_job(job_id)
            job = await self._job_model.get({"job_id": job_id})
            
            if ap_job is None or job is None:
                return JobResponse.fail(status=404, message="Job not found")

            ap_job.modify(**changes)
            updates = {key: value for key, value in changes if hasattr(job, key)}
            await job.update(**updates)
            return JobResponse.success(
                    job_id=job_id,
                    job=job,
                    create_dt=job.create_dt,
                    last_update=self._datetime.now())
        except Exception as e:
            return JobResponse.fail(status=500, message=str(e))
 
    async def delete_job(self, job_id: str) -> JobResponse:
        try:
            ap_job = self._async_scheduler.get_job(job_id)
            job = await self._job_model.get({"job_id": job_id})

            if ap_job is None or job is None:
                return JobResponse.fail(status=404, message="Job not found")
            
            ap_job.remove()
            await job.delete()
            return JobResponse.success(
                    job_id=job_id,
                    create_dt=job.create_dt,
                    last_update=self._datetime.now())
        except Exception as e:
            return JobResponse.fail(status=500, message=str(e))

    async def get_job(self, job_id: str) -> Any:
        try:
            ap_job = self._async_scheduler.get_job(job_id)
            job = await self._job_model.get({"job_id": job_id})

            if ap_job is None or job is None:
                return JobResponse.fail(status=404, message="Job not found")

            ap_job.remove()
            await job.delete()
            return JobResponse.success(
                    job_id=job_id,
                    job=job,
                    create_dt=job.create_dt,
                    last_update=self._datetime.now())
        except Exception as e:
            return JobResponse.fail(status=500, message=str(e))

    def start(self):
        self._async_scheduler.start()


if __name__ == "__main__":
    import asyncio
    import uvloop
    from pytz import utc
    from ..db.client import create_client
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.jobstores.mongodb import MongoDBJobStore
    from apscheduler.executors.asyncio import AsyncIOExecutor
    from apscheduler.executors.pool import (
        ThreadPoolExecutor, ProcessPoolExecutor
    )

    import logging

    logging.basicConfig()
    logging.getLogger('apscheduler').setLevel(logging.DEBUG)

    async def simple_test_job():
            print("started!")
            print("working...!")
            await asyncio.sleep(5)
            print("finished!")

    async def simple_external_test():
        print("working outside of job service.")
        print("started!")
        print("working...!")
        await asyncio.sleep(2)
        print("finished!")

    async def test_job_service(db_client, db_name, scheduler, jobs: List[Callable]):
        # Pitfall! You should never create a local function as a job function
        # The apscheduler will not be able to resolve its caller.
        # Pass them as argument instead.
        
        Job.db = db_client[db_name]
        
        async_job_service = AsyncJobService(
            async_scheduler=scheduler
        )
        
        # for job_func in jobs:
        #     # job = scheduler.add_job(job_func, trigger='interval', seconds=5)
        #     response = await async_job_service.add_job(
        #         func=job_func, trigger='interval', seconds=5)
        #     print(response)
        
        return async_job_service
        
    def create_scheduler():
        jobstores = {
            'default': MongoDBJobStore(client=db_client.delegate)
        }
        executors = {
            'default': AsyncIOExecutor(),
            'processpool': ProcessPoolExecutor(5)
        }
        job_defaults = {
            'coalesce': False,
            'max_instances': 3
        }
        return AsyncIOScheduler(
            jobstores=jobstores, executors=executors,
            job_defaults=job_defaults, timezone=utc
        )
        

    db_client = create_client(host='localhost',
                              username='admin',
                              password='root',
                              port=27017,
                              db_name='spiderDB')
    async_scheduler = create_scheduler()
    # async_scheduler.start()
    uvloop.install()
    loop = asyncio.get_event_loop()
    try:
        job_service = loop.run_until_complete(
            test_job_service(
                db_client,
                'spiderDB',
                async_scheduler,
                [simple_test_job, simple_external_test]))
        job_service.start()
        loop.run_forever()
    except (KeyboardInterrupt, SystemExit):
        pass
