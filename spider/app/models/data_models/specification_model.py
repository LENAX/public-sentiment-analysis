from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime, timedelta
from ..request_models import ScrapeRules
from ..db_models import Specification as SpecificationDBModel
from ...enums import JobType
from uuid import UUID
from motor.motor_asyncio import AsyncIOMotorDatabase
import re
from devtools import debug


class SpecificationData(BaseModel):
    """ Specification Data model
    
    Fields:
        specification_id: Optional[UUID]
        urls: Optional[List[str]]
        job_type: Optional[JobType]
        scrape_rules: Optional[ScrapeRules]
    """

    specification_id: Optional[UUID]
    urls: Optional[List[str]]
    job_name: Optional[str]
    job_type: Optional[JobType]
    scrape_rules: Optional[ScrapeRules]
    
    class Config:
        use_enum_values = True

    def __hash__(self):
        return hash(self.__repr__())

    @classmethod
    def from_db_model(cls, model_instance: SpecificationDBModel) -> "SpecificationData":
        return cls.parse_obj(model_instance)

    def to_db_model(self) -> SpecificationDBModel:
        pass
    
    @validator('urls')
    def validate_urls(cls, value):
        debug(value)
        if value is None or len(value) == 0:
            return []
        else:
            for url in value:
                url_matched = re.match(
                    r"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)",
                    url)
                debug(url_matched)
                if url_matched is None:
                    raise ValueError(f'{url} is not a valid URL.')
            return value
