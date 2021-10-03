from data_services.news.app.models.data_models.word_cloud import WordCloud
from typing import Optional
from .db_model import DBModel
from ..data_models import NewsWordCloud
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import Field
from uuid import UUID, uuid5, NAMESPACE_OID


class WordCloudDBModel(DBModel, NewsWordCloud):
    __collection__: str = "WordCloud"
    __db__: AsyncIOMotorDatabase

    word_cloud_id: UUID = Field(
        default_factory=lambda: uuid5(
            NAMESPACE_OID, f"WordCloud_Object_{datetime.now().timestamp()}"))
