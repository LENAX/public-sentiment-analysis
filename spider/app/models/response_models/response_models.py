from .base import ResponseModel
from typing import Optional, List, Any
from ..data_models import JobStatus, JobResult, HTMLData
from ..request_models import ResultQuery

class JobCreationResponse(ResponseModel):
    creation_status: JobStatus


class JobResultResponse(ResponseModel):
    job_result: JobResult


class ResultQueryResponse(ResponseModel):
    data: List[HTMLData]
    query: ResultQuery

class SinglePageResponse(ResponseModel):
    data: HTMLData