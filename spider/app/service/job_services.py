from typing import List, Any
from .base_services import BaseJobService
from ..models import (
    JobSpecification
)
from ..models.db_models import HTMLData, JobStatus, Job
from datetime import datetime, timedelta
from ..enums import JobType, JobState
from uuid import uuid4


class JobService(BaseJobService):
    """ Provides spider job management

    JobService takes a job specification, a work function, and a background task scheduler to run a job
    """
    
    def __init__(self, job_db_model: JobSpecification, work_func: Any, background_task_scheduler: Any) -> None:
        self.task_scheduler = background_task_scheduler

    
    def start(self, **kwargs) -> JobStatus:
        """ Start a job
        """
        try:
            self.task_scheduler.add_task(self.work_func, **kwargs)
            self.job_status.current_state = JobState.WORKING

        except Exception as e:
            raise e
