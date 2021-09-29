from .db_model import DBModel
from ..data_models import News
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import Field
from uuid import UUID, uuid5, NAMESPACE_OID


class NewsDBModel(DBModel, News):
    __collection__: str = "News"
    __db__: AsyncIOMotorDatabase

    news_id: UUID = Field(
        default_factory=lambda: uuid5(
            NAMESPACE_OID, f"News_Object_{datetime.now().timestamp()}"))
