from ..data_models import WordCloud
from .db_model import DBModel


class WordCloudDBModel(DBModel, WordCloud):
    __collection__: str = "WordCloud"

