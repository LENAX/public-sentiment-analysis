from .base import ResponseModel
from typing import Optional, List, Any
from ..data_models import JobCreationStatus, JobResult, HTMLData
from ..request_models import ResultQuery

class JobCreationResponse(ResponseModel):
    creation_status: JobCreationStatus


class JobResultResponse(ResponseModel):
    job_result: JobResult


class ResultQueryResponse(ResponseModel):
    data: List[HTMLData]
    query: ResultQuery
