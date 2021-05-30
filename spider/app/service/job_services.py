from typing import List, Any
from .base_services import BaseJobService
from ..models import (
    JobSpecification
)
from ..models.db_models import HTMLData, JobStatus
from datetime import datetime, timedelta
from ..enums import JobType, JobState
from uuid import uuid4


class JobService(BaseJobService):
    """ Provides spider job management

    JobService takes a job specification, a work function, and a background task scheduler to run a job
    """
    
    def __init__(self, job_spec: JobSpecification, work_func: Any, background_task_scheduler: Any) -> None:
        self.job_spec = job_spec
        self.job_id = str(uuid4())
        self.job_status = JobStatus(
            job_id=self.job_id,
            create_dt=datetime.now(),
            page_count=0,
            specification=self.job_spec,
            current_state=JobState.PENDING,
            time_consumed=timedelta(seconds=0)
        )
        self.work_func = work_func
        self.task_scheduler = background_task_scheduler

    
    def start(self, **kwargs) -> JobStatus:
        """ Start a job
        """
        try:
            self.task_scheduler.add_task(self.work_func, **kwargs)
            self.job_status.current_state = JobState.WORKING

        except Exception as e:
            raise e
