from ..data_models import Subscription
from .db_model import DBModel


class SubscriptionDBModel(DBModel, Subscription):
    __collection__: str = "Subscription"

