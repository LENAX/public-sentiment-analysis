from pydantic import BaseModel
from typing import Any

class ResponseModel(BaseModel):
    status_code: int
    message: str
    data: Any

    @classmethod
    def success(cls, data=None) -> "ResponseModel":
        return cls(data=data,
                   status_code=200,
                   message="success")

    @classmethod
    def fail(cls, status_code: int, message: str) -> "ResponseModel":
        return cls(status_code=status_code, message=message)
