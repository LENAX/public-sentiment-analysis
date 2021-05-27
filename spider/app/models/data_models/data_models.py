
from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime
from ..request_models import (
    JobSpecification
)
from ...enums import JobStatus

class JobCreationStatus(BaseModel):
    job_id: str
    create_dt: datetime
    specification: JobSpecification


class JobResult(BaseModel):
    job_id: str
    status: JobStatus
    message: str
    data: Any


class HTMLData(BaseModel):
    html: str
    domain: str
    keywords: Optional[List[str]]
