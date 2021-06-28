from pydantic import BaseModel
from typing import Optional
from ...enums import JobState
from uuid import UUID
from datetime import datetime
from ..db_models import Job


class JobData(BaseModel):
    """ Defines a job managed by job services
    
    Fields:
        field_name: str,
        field_value: str  
    """
    job_id: UUID
    name: str
    description: str = ""
    current_state: JobState
    next_run_time: Optional[datetime]

    class Config:
        use_enum_values = True

    def __hash__(self):
        return hash(self.__repr__())

    @classmethod
    def from_db_model(cls, model_instance: Job) -> "JobData":
        return cls.parse_obj(model_instance)