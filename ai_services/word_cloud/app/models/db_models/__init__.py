from .word_cloud import WordCloudDBModel

def bind_db_to_all_models(db_client, db_name: str) -> None:
    db = db_client[db_name]
    WordCloudDBModel.db = db
    
    