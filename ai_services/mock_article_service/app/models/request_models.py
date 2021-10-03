from pydantic import BaseModel


class ArticleServiceArgs(BaseModel):
    theme_id: int
    key_word: str
    title: str
    content: str


class WordCloudRequestArgs(BaseModel):
    theme_id: int
    key_word: str
    title: str
    content: str
