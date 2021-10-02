from pydantic import BaseModel

class ArticleCategory(BaseModel):
    whether_medical_result: bool
