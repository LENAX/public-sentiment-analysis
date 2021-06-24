from .mongo_model import MongoModel
from typing import Optional, List, Any
from datetime import date, datetime, timedelta
from ..request_models import JobSpecification
from ...enums import JobState
from uuid import UUID
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson.objectid import ObjectId


class JobStatus(MongoModel):
    job_id: UUID
    create_dt: datetime
    page_count: int = 0
    time_consumed: Optional[timedelta]
    current_state: JobState
    specification: JobSpecification


class Job(MongoModel):
    __collection__: str = "Job"
    __db__: AsyncIOMotorDatabase

    id: Optional[Any]
    job_id: UUID
    name: str
    description: str = ""
    current_state: JobState
    next_run_time: Optional[datetime]
    detail_id: Optional[UUID]
    spec_id: Optional[UUID]
    user_id: Optional[UUID]
    project_id: Optional[UUID]
    tenant_id: Optional[UUID]

    class Config:
        use_enum_values = True


if __name__ == "__main__":
    import uuid
    import asyncio
    from datetime import datetime
    from motor.motor_asyncio import AsyncIOMotorClient
    from bson.objectid import ObjectId


    def create_client(host: str, username: str,
                    password: str, port: int,
                    db_name: str) -> AsyncIOMotorClient:
        return AsyncIOMotorClient(
            f"mongodb://{username}:{password}@{host}:{port}/{db_name}?authSource=admin")

    db_client = create_client(host='localhost',
                              username='admin',
                              password='root',
                              port=27017,
                              db_name='spiderDB')

    async def test_job(db_client, db_name):
        # Pitfall!! Remember to set db!!
        Job.db = db_client[db_name]

        # await db_client.get_collections()

        job_id = uuid.uuid4()
        test_job = Job(
            id=ObjectId(),
            job_id=job_id,
            name="test",
            description="a test job",
            current_state=JobState.WORKING,
            next_run_time=datetime(2021,6,30,9,0,0)
        )
        await test_job.save()
        jobs = await Job.get({"job_id": str(job_id)})
        fetched = jobs[0]
        assert fetched.job_id == job_id
        print(test_job)
        print(fetched)

        await test_job.update({"name": "updated_test"})
        jobs = await Job.get({"job_id": str(job_id)})
        fetched = jobs[0]
        assert fetched.name == "updated_test"
        # print(test_job)
        print(f"updated: {fetched}!!!!!")

        await test_job.delete()
        jobs = await Job.get({"job_id": str(job_id)})
        assert len(jobs) == 0
        print("test completed!")

    # You can't do it this way! Because Motor has its own loop!!
    # asyncio.run(test_job(db_client, "spiderDB"))
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test_job(db_client, "spiderDB"))

