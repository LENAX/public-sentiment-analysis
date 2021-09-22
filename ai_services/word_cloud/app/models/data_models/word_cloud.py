from pydantic import BaseModel
from typing import Optional, List, Tuple

class WeightedWord(BaseModel):
    word: Optional[str]
    weight: Optional[float]

class WordCloud(BaseModel):
    content: Optional[List[WeightedWord]]
    
    @classmethod
    def parse_obj(cls, wc: List[Tuple[str, float]]):
        wc_list = []
        try:
            wc_list = [WeightedWord(word=word, weight=weight) for word, weight in wc]
            return cls(content=wc_list)
        except:
            return cls(content=[])
            
    
    

