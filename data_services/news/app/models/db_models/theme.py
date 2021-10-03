from data_services.news.app.models.data_models.theme import Theme
from typing import Optional
from .db_model import DBModel
from ..data_models import Theme
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import Field
from uuid import UUID, uuid5, NAMESPACE_OID


class ThemeDBModel(Theme, DBModel):
    """ Defines a set of keywords for media monitoring
    
    Fields:
        areaKeywords
    """
    __collection__: str = "Theme"
    __db__: AsyncIOMotorDatabase

    theme_id: UUID = Field(
        default_factory=lambda: uuid5(NAMESPACE_OID, f"Theme_Object_{datetime.now().timestamp()}"))
    
