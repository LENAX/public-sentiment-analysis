from pydantic import BaseModel

class ArticleSummary(BaseModel):
    abstract_result: str