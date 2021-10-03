from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class Keyword(BaseModel):
    """ Defines a keywords for media monitoring
    
    Fields:
        keywordType: Optional[int]
        keyword: Optional[str]
    """
    keywordType: Optional[int]
    keyword: Optional[str]
    

class Theme(BaseModel):
    """ Defines a set of keywords for media monitoring
    
    Fields:
        themeId: Optional[int]
        areaKeywords: Optional[List[str]]
        themeKeywords: Optional[List[Keyword]]
        epidemicKeywords: Optional[List[str]]
    """
    themeId: Optional[int]
    areaKeywords: Optional[List[str]]
    themeKeywords: Optional[List[Keyword]]
    epidemicKeywords: Optional[List[str]]
