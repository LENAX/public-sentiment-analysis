from typing import List
from typing_extensions import Literal
from pydantic import BaseModel


class ArticleSummary(BaseModel):
    abstract_result: str


class ArticlePopularity(BaseModel):
    sim_result: int
    hot_value: int

class ArticleCategory(BaseModel):
    whether_medical_result: Literal[1,0]


class WeightedWord(BaseModel):
    word: str
    weight: float


class WordCloud(BaseModel):
    word_cloud: List[WeightedWord]
