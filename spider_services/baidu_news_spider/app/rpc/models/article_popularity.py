from pydantic import BaseModel

class ArticlePopularity(BaseModel):
    sim_result: int
    hot_value: int