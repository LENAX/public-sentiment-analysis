
from pydantic import BaseModel
from typing import Optional, List, Any, Union, AnyStr
from datetime import datetime, timedelta
from ..request_models import (
    JobSpecification
)
from ...enums import JobState, ParseRuleType
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
        name: Optional[str]
        url: str
        domain: Optional[str]
    """
    name: Optional[str] = None
    url: str
    domain: Optional[str] = None

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)
        parsed_domain = domain_pattern.findall(self.url)

        if self.domain is None and len(parsed_domain):
            # auto fills domain name if not provided
            self.domain = parsed_domain[0]

    def __hash__(self):
        return hash(self.__repr__())


class HTMLData(BaseModel):
    """ Builds a html data representation

    Fields:
        url: str
        html: str
        create_dt: datetime
        job_id: Optional[str]
        keywords: Optional[List[str]] = []
    """
    url: str
    html: str
    create_dt: datetime


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


class ParseRule(BaseModel):
    """ Defines the parse rule for a parser

    Fields:
        field_name: str,
        rule: str,
        rule_type: ParseRuleType        
    """
    field_name: Optional[str]
    rule: str
    rule_type: ParseRuleType


class ParseResult(BaseModel):
    """ Defines the parse result from a parser
    
    Fields:
        field_name: str,
        field_value: str  
    """
    name: str
    value: str

    def __hash__(self):
        return hash(self.__repr__())


class CrawlResult(BaseModel):
    """ Defines a page visited by crawl algorithm
    
    Fields:
        id: int,
        name: Optional[str],
        url: str,
        page_src: str,
        relative_depth: int,
        neighbors: List[int] = []
    """
    # TODO: implement a graph node like structure
    id: int
    name: Optional[str]
    url: str
    page_src: str
    relative_depth: int
    neighbors: List[int] = []

    def __hash__(self):
        return hash(self.__repr__())

    def __str__(self):
        return f"""<CrawlResult id={self.id}" name={self.name} url={self.url} 
                                page_src={self.page_src[:100]} 
                                relative_depth={self.relative_depth}
                                neighbors={self.neighbors}>"""


