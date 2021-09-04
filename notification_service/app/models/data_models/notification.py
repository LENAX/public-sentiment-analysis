from pydantic import BaseModel
from typing import Optional

class Notification(BaseModel):
    sender: str
    receiver: Optional[str]
    body: str
    

