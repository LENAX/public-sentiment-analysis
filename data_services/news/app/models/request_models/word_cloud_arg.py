from pydantic import BaseModel

class WordCloudRequestArgs(BaseModel):
    appId: str
    themeId: int
    
