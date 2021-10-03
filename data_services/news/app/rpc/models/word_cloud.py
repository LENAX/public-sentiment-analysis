from typing import List
from pydantic import BaseModel

class WeightedWord(BaseModel):
    word: str
    weight: float

class WordCloud(BaseModel):
    word_cloud: List[WeightedWord]
