from pydantic import BaseModel
from typing import Optional


class MigrationRank(BaseModel):
    date: Optional[str]
    to_province: Optional[str]
    to_province_areaCode: Optional[str]
    from_province: Optional[str]
    from_province_areaCode: Optional[str]
    direction: Optional[str]
    value: Optional[float]
    
    
    @classmethod
    def from_db_model(cls, model_instance) -> "MigrationRank":
        return cls.parse_obj(model_instance)
