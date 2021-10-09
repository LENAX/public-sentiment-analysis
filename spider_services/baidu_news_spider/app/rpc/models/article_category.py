from pydantic import BaseModel

class ArticleCategory(BaseModel):
    is_medical_article: bool
