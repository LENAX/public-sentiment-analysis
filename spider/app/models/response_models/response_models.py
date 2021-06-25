from .base import ResponseModel
from typing import Optional, List, Any, Union
from ..data_models import JobResult, HTMLData
from ..db_models import Job
from ..request_models import ResultQuery
from datetime import datetime
from uuid import UUID

class JobResponse(ResponseModel):
    job_id: Optional[Union[str, UUID]]
    job: Optional[Job]
    create_dt: Optional[datetime]
    last_update: Optional[datetime]
    
    @classmethod
    def success(cls, job_id: str, create_dt: datetime,
                last_update: datetime, job: Job = None) -> "JobResponse":
        return cls(job_id=job_id,
                   job=job,
                   create_dt=create_dt,
                   last_update=last_update,
                   status_code=200,
                   message="success")

    @classmethod
    def fail(cls, status_code: int, message: str) -> "JobResponse":
        return cls(status_code=status_code, message=message)

class JobResultResponse(ResponseModel):
    job_result: JobResult


class ResultQueryResponse(ResponseModel):
    data: List[HTMLData]
    query: ResultQuery

class SinglePageResponse(ResponseModel):
    data: HTMLData
