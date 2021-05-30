
from pydantic import BaseModel
from typing import Optional, List, Any, Union
from datetime import datetime, timedelta
from ..request_models import (
    JobSpecification
)
from ...enums import JobState
from ...utils.regex_patterns import domain_pattern

class DataModel(BaseModel):
    pass

class JobStatus(BaseModel):
    job_id: str
    create_dt: datetime
    page_count: int = 0
    time_consumed: Optional[timedelta]
    specification: JobSpecification

    def save(self, db_client, collection):
        pass


class JobResult(BaseModel):
    job_id: str
    status: JobState
    message: str
    data: Any


class URL(BaseModel):
    """ Holds an url and its domain name.

    If domain name is not specified, it will be guessed from the url

    Fields:
        url: str
        domain: Optional[str]
    """
    url: str
    domain: Optional[str] = None

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        parsed_domain = domain_pattern.findall(self.url)

        if self.domain is None and len(parsed_domain):
            # auto fills domain name if not provided
            self.domain = parsed_domain[0]


class HTMLData(BaseModel):
    """ Builds a html data representation

    Fields:
        url: URL
        html: str
        create_dt: datetime
        job_id: Optional[str]
        keywords: Optional[List[str]] = []
    """
    url: URL
    html: str
    create_dt: datetime
    job_id: Optional[str]
    keywords: Optional[List[str]] = []


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
