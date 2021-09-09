from pydantic import BaseModel
from typing import Optional

class Subscription(BaseModel):
    subscriber_name: Optional[str]
    subscriber_id: Optional[str]
    subscriber_id_type: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    subscription_type: Optional[str]
    service_name: Optional[str]
    

