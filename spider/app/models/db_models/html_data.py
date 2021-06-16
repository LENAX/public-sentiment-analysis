from .mongo_model import MongoModel
from typing import Optional, List
from datetime import datetime
from ..data_models import URL
from uuid import UUID

class HTMLData(MongoModel):
    """ Builds a html data representation

    Fields:
        url: URL
        html: str
        create_dt: datetime
        job_id: Optional[str]
        keywords: Optional[List[str]] = []
    """
    url: URL
    html: str
    create_dt: datetime

