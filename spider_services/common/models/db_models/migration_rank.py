from pydantic import BaseModel, Field
from typing import Optional
from .db_model import DBModel
from ..data_models import MigrationRank
from datetime import datetime


class MigrationRankDBModel(DBModel, MigrationRank):
    __collection__: str = "MigrationRank"
    last_update: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%dT%H:%M:%S"))
