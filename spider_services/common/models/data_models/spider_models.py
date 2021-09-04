""" Data models used by a spider and spider services

@Author Steve Lan
"""

from pydantic import BaseModel
from typing import Optional, List, Any, Union, AnyStr, Dict
from datetime import datetime, timedelta
from ...utils.regex_patterns import domain_pattern


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

