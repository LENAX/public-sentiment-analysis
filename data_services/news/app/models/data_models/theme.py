from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class Keyword(BaseModel):
    keywordType: Optional[int]
    keyword: Optional[str]
    

class Theme(BaseModel):
    """ Defines a set of keywords for media monitoring
    
    Fields:
        areaKeywords
    """
    areaKeywords: Optional[List[str]]
    themeKeywords: Optional[List[Keyword]]
    epidemicKeywords: Optional[List[str]]
