from spider.app import db
from typing import List, Any, Callable, Union, TypeVar
from collections.abc import Coroutine
from .base_services import BaseJobService
from apscheduler.schedulers.base import BaseScheduler
from apscheduler.triggers.base import BaseTrigger
from apscheduler.job import Job as APJob
from ..models.response_models import (
    JobResponse, ResponseModel
)
from ..models.db_models import JobStatus, Job
from datetime import datetime, timedelta
from ..enums import JobType, JobState
from uuid import uuid4, UUID
from datetime import datetime
from bson.objectid import ObjectId
from asyncio import Lock

TZInfo = TypeVar("TZInfo")

class AsyncJobService(BaseJobService):
    """ Provides async job management using APScheduler

    """
    def __init__(self,
                 async_scheduler: BaseScheduler,
                 job_model: Job = Job,
                 job_status_model: JobStatus = JobStatus,
                 oid_generator: ObjectId = ObjectId,
                 uuid_generator: Callable = uuid4,
                 datetime: datetime = datetime,
                 lock: Lock = Lock) -> None:
        self._async_scheduler = async_scheduler
        self._job_model = job_model
        self._job_status_model = job_status_model
        self._oid_generator = oid_generator
        self._uuid_generator = uuid_generator
        self._datetime = datetime
        self._lock = lock() # is lock necessary?

    async def add_job(self, func: Callable,
                  trigger: BaseTrigger = None, name: str = None,
                  description: str = "", misfire_grace_time: int = None,
                  coalesce: bool = False, max_instances: int = 1,
                  next_run_time:str = None, jobstore: str = 'default',
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
            ap_job.modify(**changes)
            updates = {key: changes[key] for key in changes}
            await self._job_model.update_one(
                query={"job_id": job_id}, update=updates)
            
            return JobResponse.success(
                    job_id=job_id,
                    last_update=self._datetime.now())
        except IndexError:
            return JobResponse.fail(status_code=404, message="Job not found")
        except Exception as e:
            return JobResponse.fail(status_code=500, message=str(e))

    async def _update_next_run_time(self, job_id: str, 
                                    write_back_to_db: bool = False) -> Job:
        """ Update job's next run time from apscheduler's job
        """
        ap_job = self._async_scheduler.get_job(job_id)
        job = await self._job_model.get_one({'job_id': job_id})
        job.next_run_time = ap_job.next_run_time

        if write_back_to_db:
            await job.update({"next_run_time": ap_job.next_run_time})
        
        return job

    async def reschedule_job(self, job_id: str, trigger: str = 'cron', 
                             year: Union[int, str] = None, month: Union[int, str] = None,
                             day: Union[int, str] = None, week: Union[int, str] = None,
                             day_of_week: Union[int, str] = None, hour: Union[int, str] = None,
                             minute: Union[int, str] = None, second: Union[int, str] = None,
                             start_date: Union[datetime, str] = None,
                             end_date: Union[datetime, str] = None,
                             timezone: Union[TZInfo, str] = None, **kwargs) -> JobResponse:
        try:
            if trigger != 'cron':
                self._async_scheduler.reschedule_job(job_id=job_id, trigger=trigger, **kwargs)
            else:
                self._async_scheduler.reschedule_job(
                    job_id=job_id, trigger='cron', year=year, month=month, day=day,
                    week=week, day_of_week=day_of_week, hour=hour, minute=minute,
                    second=second, start_date=start_date, end_date=end_date, timezone=timezone)
            job = await self._update_next_run_time(job_id)
            return JobResponse.success(job=job)
        except Exception as e:
            return JobResponse.fail(status_code=500, message=str(e))
 
    async def delete_job(self, job_id: str) -> JobResponse:
        try:
            self._async_scheduler.remove_job(job_id)
            await self._job_model.delete_one({"job_id": job_id})

            return JobResponse.success()
        except Exception as e:
            return JobResponse.fail(status_code=500, message=str(e))

    async def delete_jobs(self, job_ids: List[str]) -> JobResponse:
        try:
            job_id_set = set(job_ids)
            ap_jobs_to_remove = []
            for job in self._async_scheduler.get_jobs():
                if job.id in job_id_set:
                    job.remove()
                    ap_jobs_to_remove.append(job)
            query = {"job_id": {"$in": [job.id for job in ap_jobs_to_remove]}}
            await self._job_model.delete_many(query)

            return JobResponse.success()
        except Exception as e:
            return JobResponse.fail(status_code=500, message=str(e))

    async def get_job(self, job_id: str) -> JobResponse:
        try:
            ap_job = self._async_scheduler.get_job(job_id)
            job = await self._job_model.get({"job_id": job_id})
            job.next_run_time = ap_job.next_run_time

            return JobResponse.success(
                    job_id=job_id,
                    job=job[0])
        except IndexError:
            return JobResponse.fail(status_code=404, message="Job not found")
        except Exception as e:
            return JobResponse.fail(status_code=500, message=str(e))
    
    async def get_running_jobs(self) -> ResponseModel:
        try:
            ap_jobs = self._async_scheduler.get_jobs()
            query = {"job_id": {"$in": [job.id for job in ap_jobs]}}
            jobs = await self._job_model.get(query)

            return ResponseModel.success(data=jobs)
        except Exception as e:
            return ResponseModel.fail(status_code=500, message=str(e))

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
    import string
    import random
    import time
    from functools import partial
    import logging

    logging.basicConfig()
    logging.getLogger('apscheduler').setLevel(logging.DEBUG)

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)


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


    async def simple_test_job():
        logger.info("inside of simple_test_job")
        print("started!")
        print("working...!")
        await asyncio.sleep(5)
        print("finished!")

    async def simple_external_test():
        logger.info("inside of simple_external_test")
        print("working outside of job service.")
        print("started!")
        print("working...!")
        await asyncio.sleep(5)
        print("finished!")


    
    async def job_func():
        job_id = random.randint(0,100)
        print_stuff = ''.join(random.choices(
            string.ascii_uppercase + string.digits, k=job_id))
        sleep_time = random.randint(0,10)
        logger.info(f"inside test job {job_id}")
        print(f"I am job {job_id}")
        print(print_stuff)
        print("started!")
        print("working...!")
        await asyncio.sleep(sleep_time)
        print("finished!")

        


    async def test_add_job(async_job_service: AsyncJobService, jobs: List[Callable]):
        # Pitfall! You should never create a local function as a job function
        # The apscheduler will not be able to resolve its caller.
        # Pass them as argument instead.
        print("\n****************")
        logger.info("Test adding....")
        try:
            # test add
            for job_func in jobs:
                response = await async_job_service.add_job(
                    func=job_func, trigger='interval', seconds=10)
                logger.info(f"get response from async_job_service: {response}")
                assert response.status_code == 200
            logger.info("Test adding passed!")
            print("****************\n")
        except AssertionError:
            logger.error(
                f"Excepted 200 from response. Got {response.status_code} instead")
            print("****************\n")

    # get test
    async def test_get_jobs(async_job_service: AsyncJobService, jobs: List[Callable]):
        print("\n****************")
        logger.info("Test getting jobs....")
        try:
            resp = await async_job_service.get_running_jobs()
            logger.debug(f"Added jobs are {resp.data}")
            assert len(resp.data) == len(jobs)
            logger.info("Test get_jobs passed!")
            print("****************\n")
        except AssertionError:
            logger.error(f"Excepted add {len(jobs)} jobs. "
                         f"Added {len(resp.data)} jobs instead.")
            logger.debug(f"added_jobs: {resp.data}")
            print("****************\n")
    
    # update test
    async def test_update_job_attributes(async_job_service):
        print("\n****************")
        logger.info("Test update job names and descriptions")

        try:
            response = await async_job_service.get_running_jobs()
            logger.debug(f"Added jobs are {response.data}")

            for job in response.data:
                logger.debug(f"before update: {job}")
                update_resp = await async_job_service.update_job(
                                        job.job_id,
                                        name=f"updated_{job.name}",
                                        description=f"updated_{job.description}")
                assert update_resp.status_code == 200
                updated_job = await async_job_service.get_job(job_id=update_resp.job_id)
                assert updated_job.job.name.startswith("updated_")
                assert updated_job.job.description.startswith("updated_")
                logger.info("Test update_jobs passed!")
                print("****************\n")
        except AssertionError as e:
            logging.error("modification failed!")
            # logger.debug(f"added_jobs: {response}")
            logger.debug(f"updated: {update_resp}")
            print("****************\n")
            raise e

    # update test
    async def test_reschedule_job(async_job_service):
        print("\n****************")
        logger.info("Test reschedule jobs")

        try:
            response = await async_job_service.get_running_jobs()
            logger.debug(f"Added jobs are {response.data}")

            for job in response.data:
                logger.debug(f"before update: {job}")
                logging.info(f"type job_id: {type(job.job_id)}")
                update_resp = await async_job_service.reschedule_job(
                                        job.job_id, day_of_week='mon-fri',
                                        hour=random.randint(0, 11),
                                        minute=random.randint(1, 59))
                assert update_resp.status_code == 200
                logger.debug(f"updated job: {update_resp.job}!!!")
                logger.info("Test reschedule passed!")
        except AssertionError as e:
            logging.error("Reschedule failed!")
            logger.debug(f"added_jobs: {update_resp}")
            print("****************\n")
            raise e


    # delete test
    async def test_delete_jobs(async_job_service):
        print("\n****************")
        logger.info("Test delete jobs")

        try:
            response = await async_job_service.get_running_jobs()
            logger.debug(f"Added jobs are {response.data}")

            for job in response.data:
                delete_response = await async_job_service.delete_job(job_id=job.job_id)
                assert delete_response.status_code == 200
                logger.debug(f"successfully deleted job {job.job_id}")

            response = await async_job_service.get_running_jobs()
            assert len(response.data) == 0
            logger.info("Test delete passed!")
            print("****************\n")

        except AssertionError:
            logger.debug(f"added_jobs: {response}")
            print("****************\n")
    
    async def clean_up(db_client):
        await db_client.spiderDB.Job.drop()
        await db_client.apscheduler.jobs.drop()


    db_client = create_client(host='localhost',
                              username='admin',
                              password='root',
                              port=27017,
                              db_name='spiderDB')
    async_scheduler = create_scheduler()
    async_scheduler.start()
    
    Job.db = db_client['spiderDB']


    loop = asyncio.get_event_loop()
    async_job_service = AsyncJobService(async_scheduler=async_scheduler)
    test_jobs = [job_func for i in range(2)]

    # print(test_jobs)
    test_cases = [
        test_add_job(
            async_job_service,
            test_jobs),
        test_get_jobs(
            async_job_service,
            test_jobs),
        test_update_job_attributes(async_job_service),
        test_reschedule_job(async_job_service),
        test_delete_jobs(async_job_service),
    ]

    try:
        for test_case in test_cases:
            loop.run_until_complete(test_case)
            # time.sleep(3)
        loop.run_forever()
    except Exception as e:
        print(e)
    finally:
        loop.run_until_complete(clean_up(db_client))

