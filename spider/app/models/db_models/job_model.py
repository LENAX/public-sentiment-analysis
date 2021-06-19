from .mongo_model import MongoModel
from typing import Optional, List, Any
from datetime import datetime, timedelta
from ..request_models import JobSpecification
from ...enums import JobState
from uuid import UUID
from motor.motor_asyncio import AsyncIOMotorDatabase


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


    job_id: UUID
    name: str
    description: str = ""
    current_state: JobState
    schedule_id: Optional[UUID]
    detail_id: Optional[UUID]
    spec_id: Optional[UUID]
    user_id: Optional[UUID]
    project_id: Optional[UUID]
    tenant_id: Optional[UUID]
