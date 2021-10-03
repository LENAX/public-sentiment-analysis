from pydantic import BaseModel
from typing import Optional, List, Tuple

class WordCloud(BaseModel):
    word: Optional[str]
    weight: Optional[float]

    
class NewsWordCloud(BaseModel):
    themeId: Optional[int]
    createDt: Optional[str]
    wordCloudPastWeek: Optional[List[WordCloud]]
    wordCloudPastMonth: Optional[List[WordCloud]]
    
    

