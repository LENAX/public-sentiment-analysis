from typing import List, Optional
from pydantic import BaseModel
from ..data_models import News

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
    articles: Optional[List[News]]
    createDt: Optional[str]

