from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class News(BaseModel):
    """ Defines a news article
    
    Fields:
        title: Optional[str]
        source: Optional[str]
        date: Optional[str]
        publishDate: Optional[str]
        link: Optional[str]
        popularity: Optional[int]
        summary: Optional[str]
        content: Optional[str]
    """
    title: Optional[str]
    source: Optional[str]
    date: Optional[str]
    publishDate: Optional[datetime]
    link: Optional[str]
    popularity: Optional[int]
    summary: Optional[str]
    content: Optional[str]
    is_medical_article: bool = False
