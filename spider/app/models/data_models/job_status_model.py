from pydantic import BaseModel
from typing import List, Any, Union, Dict
from ...enums import JobState

class JobStatus(BaseModel):
    status: JobState

    class Config:
        use_enum_values = True
