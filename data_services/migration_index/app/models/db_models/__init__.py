from .migration_index import MigrationIndexDBModel
from .migration_rank import MigrationRankDBModel


def bind_db_to_all_models(db_client, db_name: str) -> None:
    db = db_client[db_name]
    MigrationRankDBModel.db = db
    MigrationIndexDBModel.db = db
    
    
