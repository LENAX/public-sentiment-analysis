from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from ..data_models import News
import ujson

class Article(BaseModel):
    title: Optional[str]
    source: Optional[str]
    date: Optional[str]
    publishDate: Optional[datetime]
    link: Optional[str]
    popularity: Optional[int]
    summary: Optional[str]
    keyword: Optional[str]
    is_medical_article: bool = False
    themeId: Optional[int]
    create_dt: Optional[str]

class NewsResponse(BaseModel):
    """NewsResponse

    Args:
        total: Optional[int]
        themeId: Optional[int]
        articles: Optional[List[News]]
        createDt: Optional[str]
    """
    total: Optional[int]
    themeId: Optional[int]
    articles: Optional[List[Article]]
    createDt: Optional[str]

    class Config:
        json_loads = ujson.loads
        json_dumps = ujson.dumps
