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

class AsyncJobService(BaseJobService):
    """ Provides async job management using APScheduler

    """
    def __init__(self,
                 async_scheduler: BaseScheduler,
                 job_model: Job = Job,
                 job_status_model: JobStatus = JobStatus,
                 id_generator: Callable = uuid4,
                 datetime: datetime = datetime) -> None:
        self._async_scheduler = async_scheduler
        self._job_model = job_model
        self._job_status_model = job_status_model
        self._id_generator = id_generator
        self._datetime = datetime

    async def add_job(self, func: Callable,
                  trigger: BaseTrigger = None, name: str = None,
                  description: str = "", misfire_grace_time: int = None,
                  coalesce: bool = False, max_instances: int = 1,
                  next_run_time=None, jobstore: str = 'default',
                  executor: str = 'default', replace_existing: bool = False,
                  **trigger_args) -> JobResponse:
        job_id = self._id_generator()
        # might be blocking under the hood...
        # TODO: run in a separate thread to avoid blocking the event loop
        try:
            ap_job = self._async_scheduler.add_job(
                func=func, trigger=trigger, id=job_id, name=name,
                misfire_grace_time=misfire_grace_time,
                coalesce=coalesce, max_instances=max_instances,
                next_run_time=next_run_time, jobstore=jobstore,
                executor=executor, replace_existing=replace_existing,
                **trigger_args
            )
            job = Job(
                job_id=job_id,
                name=ap_job.name,
                description=description,
                current_state=JobState.WORKING,
                next_run_time=ap_job.next_run_time
            )
            await job.save()
            create_dt = self._datetime.now()
            return JobResponse.success(
                        job_id=job_id,
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



if __name__ == "__main__":
    import asyncio

    