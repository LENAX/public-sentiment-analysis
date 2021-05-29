from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
from ...enums import ContentType


class JobSpecification(BaseModel):
    """ Holds specification for a spider job

    Fields:
        urls: List[str]
    """
    urls: List[str]


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
