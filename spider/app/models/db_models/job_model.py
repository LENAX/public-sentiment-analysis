from .mongo_model import MongoModel
from typing import Optional, List, Any
from datetime import datetime, timedelta
from ..request_models import JobSpecification
from ...enums import JobState


class JobStatus(MongoModel):
    job_id: str
    create_dt: datetime
    page_count: int = 0
    time_consumed: Optional[timedelta]
    current_state: JobState
    specification: JobSpecification
