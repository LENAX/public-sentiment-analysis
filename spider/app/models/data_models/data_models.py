
from pydantic import BaseModel
from typing import Optional, List, Any, Union
from datetime import datetime
from ..request_models import (
    JobSpecification
)
from ...enums import JobStatus

class DataModel(BaseModel):
    pass

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
    """ Builds a html data representation

    Fields:
        html: str
        domain: str
        keywords: Optional[List[str]]
    """
    html: str
    domain: str = ''
    keywords: Optional[List[str]] = []


class URL(BaseModel):
    url: str
    domain: Optional[str]


class RequestHeader(BaseModel):
    """ Builds a request header for a spider

    Fields:
        accept: str
        authorization: Optional[str]
        user_agent: str
        cookie: Union[dict, str]
    """
    accept: str
    authorization: Optional[str] = ""
    user_agent: str
    cookie: Union[str, dict] = ""
