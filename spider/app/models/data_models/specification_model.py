from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timedelta
from ..request_models import ScrapeRules
from ..db_models import Specification as SpecificationDBModel
from ...enums import JobType
from uuid import UUID
from motor.motor_asyncio import AsyncIOMotorDatabase


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
