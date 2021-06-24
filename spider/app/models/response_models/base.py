from pydantic import BaseModel

class ResponseModel(BaseModel):
    status_code: int
    message: str

    @classmethod
    def success(cls) -> "ResponseModel":
        return cls(status_code=200,
                   message="success")

    @classmethod
    def fail(cls, status_code: int, message: str) -> "ResponseModel":
        return cls(status_code=status_code, message=message)
