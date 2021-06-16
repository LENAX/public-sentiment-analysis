from typing import Optional, List
from pydantic import BaseModel
from datetime import date, datetime
from ...enums import ContentType, JobType


class KeywordRules(BaseModel):
    include: List[str] = []
    exclude: List[str] = []


class SizeLimit(BaseModel):
    max_pages: Optional[int]
    max_size: Optional[int]


class TimeRange(BaseModel):
    past_days: Optional[int]
    date_before: Optional[date]
    date_after: Optional[date]


class RegexPattern(BaseModel):
    patterns: Optional[List[str]] = []


class ScrapeRules(BaseModel):
    """ Describes rules a spider should follow

    Fields:
        keywords: Optional[KeywordRules]
        size_limit: Optional[SizeLimit]
        time_range: Optional[TimeRange]
        regular_expressions: Optional[RegexPattern]
        max_retry: Optional[int] = 1
        max_concurrency: Optional[int] = 50
        request_params: dict = {}
    """
    keywords: Optional[KeywordRules]
    max_pages: Optional[int]
    max_size: Optional[int]
    time_range: Optional[TimeRange]
    regular_expressions: Optional[List[str]] = []
    max_retry: Optional[int] = 1
    max_concurrency: Optional[int] = 50
    request_params: dict = {}



class JobSpecification(BaseModel):
    """ Describes what kind of task a spider should perform

    Fields:
        urls: List[str]
        job_type: JobType
        scrape_rules: ScrapeRules
        data_collection: str = 'test'
        job_collection: str = "jobs"
    """
    urls: List[str]
    job_type: JobType
    scrape_rules: ScrapeRules
    data_collection: str = 'test'
    job_collection: str = "jobs"


class ResultQuery(BaseModel):
    """ Holds parameters for a result query

    Fields:
        content_type: Optional[ContentType]
        domains: Optional[List[str]]
        keywords: Optional[List[str]]
        start_dt: Optional[datetime]
        end_dt: Optional[datetime]
    """
    content_type: Optional[ContentType]
    domains: Optional[List[str]]
    keywords: Optional[List[str]]
    start_dt: Optional[datetime]
    end_dt: Optional[datetime]
