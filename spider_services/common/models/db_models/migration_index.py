from pydantic import BaseModel, Field
from typing import Optional
from .db_model import DBModel
from ..data_models import MigrationIndex
from datetime import datetime


class MigrationIndexDBModel(DBModel, MigrationIndex):
    __collection__: str = "MigrationIndex"
    last_update: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%dT%H:%M:%S"))
