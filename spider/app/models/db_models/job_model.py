from .mongo_model import MongoModel
from typing import Optional
from datetime import datetime
from ...enums import JobState
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson.objectid import ObjectId
from ..extended_types import PydanticObjectId
from pydantic import Field
from uuid import UUID, uuid5, uuid4, NAMESPACE_OID
from ...models.data_models import Schedule

class Job(MongoModel):
    __collection__: str = "Job"
    __db__: AsyncIOMotorDatabase

    id: PydanticObjectId = Field(
        default_factory=lambda: ObjectId())
    job_id: UUID = Field(
        default_factory=lambda: uuid5(
            NAMESPACE_OID, f"Job_Object_{datetime.now().timestamp()}"))

    name: str
    description: str = ""
    current_state: JobState
    schedule: Schedule
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
    from ..extended_types import PydanticObjectId


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
        test_job = Job(
            name="test",
            description="a test job",
            current_state=JobState.WORKING,
            next_run_time=datetime(2021,6,30,9,0,0)
        )
        await test_job.save()
        jobs = await Job.get({"job_id": str(test_job.job_id)})
        fetched = jobs[0]
        assert fetched.job_id == test_job.job_id
        print(test_job)
        print(fetched)

        await test_job.update({"name": "updated_test"})
        jobs = await Job.get({"job_id": str(test_job.job_id)})
        fetched = jobs[0]
        assert fetched.name == "updated_test"
        # print(test_job)
        print(f"updated: {fetched}!!!!!")

        await test_job.delete()
        jobs = await Job.get({"job_id": str(test_job.job_id)})
        assert len(jobs) == 0
        print("test completed!")

    # You can't do it this way! Because Motor has its own loop!!
    # asyncio.run(test_job(db_client, "spiderDB"))
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test_job(db_client, "spiderDB"))

