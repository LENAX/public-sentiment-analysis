from motor.motor_asyncio import AsyncIOMotorClient


def create_client(host: str, username: str,
                  password: str, port: int,
                  db_name: str) -> AsyncIOMotorClient:
    return AsyncIOMotorClient(
            f"mongodb://{username}:{password}@{host}:{port}/{db_name}?authSource=admin")
