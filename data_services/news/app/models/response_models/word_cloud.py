from typing import List, Optional
from pydantic import BaseModel
from ..data_models import NewsWordCloud

class WordCloudResponse(BaseModel):
    themeId: Optional[int]    
    createDt: Optional[str]
    wordClouds: NewsWordCloud

