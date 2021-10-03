from typing import List
from pydantic import BaseModel

class Keyword(BaseModel):
    keywordType: int
    keyword: str


class BaiduNewsSpiderArgs(BaseModel):
    url: str = "http://www.baidu.com/s?tn=news&ie=utf-8"
    past_days: int = 30
    theme_id: int
    area_keywords: List[str]
    theme_keywords: List[Keyword]
    epidemic_keywords: List[str]
