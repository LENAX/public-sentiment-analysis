from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from ..db_models import News as NewsDBModel


class NewsData(BaseModel):
    """ Defines a weather record
    
    Fields:
        field_name: Optional[Optional[str]],
        field_value: Optional[Optional[str]]  
    """
    news_id: Optional[UUID]
    url: Optional[str] = ""
    title: Optional[str] = ""
    author: Optional[str] = ""
    publish_time: datetime
    content: Optional[str] = ""
    images: List[Optional[str]] = []

    remark: Optional[str] = ""

    def __hash__(self):
        return hash(self.__repr__())

    @classmethod
    def from_db_model(cls, model_instance: NewsDBModel) -> "NewsData":
        return cls.parse_obj(model_instance)

    def to_db_model(self) -> NewsDBModel:
        pass
