from .subscription import SubscriptionDBModel

def bind_db_to_all_models(db_client, db_name: str) -> None:
    db = db_client[db_name]
    SubscriptionDBModel.db = db
    
    