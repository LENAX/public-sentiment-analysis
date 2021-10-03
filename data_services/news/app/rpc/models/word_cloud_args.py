from pydantic import BaseModel

class WordCloudRequestArgs(BaseModel):
    theme_id: int
    key_word: str
    title: str
    content: str