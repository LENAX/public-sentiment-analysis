from .mongo_model import MongoModel
from typing import Optional, List, Any
from datetime import datetime, timedelta
from ..request_models import JobSpecification, ScrapeRules
from ...enums import JobState, ContentType, JobType
from uuid import UUID
from motor.motor_asyncio import AsyncIOMotorDatabase


class Specification(MongoModel):
    __collection__: str = "Specification"
    __db__: AsyncIOMotorDatabase = None
    
    specification_id: UUID
    urls: List[str]
    source_type: ContentType
    job_type: JobType
    scrape_rules: ScrapeRules
    user_id: Optional[UUID]
    project_id: Optional[UUID]
    tenant_id: Optional[UUID]

