from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

def create_client(host: str, username: str,
                  password: str, port: int,
                  db_name: str) -> AsyncIOMotorClient:
    loop = asyncio.get_event_loop()
    # asyncio.set_event_loop(loop)
    return AsyncIOMotorClient(f"mongodb://{username}:{password}@{host}:{port}/{db_name}?authSource=admin",
                              io_loop=loop)
