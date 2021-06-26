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
        return cls(job_id=model_instance.job_id, name=model_instance.name,
                   description=model_instance.description,
                   created=model_instance.current_state,
                   next_run_time=model_instance.next_run_time,
                   current_state=model_instance.current_state)
