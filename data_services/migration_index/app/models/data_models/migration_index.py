from pydantic import BaseModel
from typing import Optional


class MigrationIndex(BaseModel):
    areaCode: Optional[str]
    date: Optional[str]
    migration_index: Optional[float]
    migration_type: Optional[str]
    
    
    @classmethod
    def from_db_model(cls, model_instance) -> "MigrationIndex":
        return cls.parse_obj(model_instance)
