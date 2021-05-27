from typing import Optional, List, Any
from pydantic import BaseModel, Field
from datetime import datetime
from dataclasses import dataclass
from ...enums import ContentType



class JobSpecification(BaseModel):
    urls: List[str]


class ResultQuery(BaseModel):
    content_type: Optional[ContentType]
    domains: Optional[List[str]]
    keywords: Optional[List[str]]
    start_dt: Optional[datetime]
    end_dt: Optional[datetime]
