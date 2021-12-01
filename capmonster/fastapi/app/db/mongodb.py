"""
MongoDB
"""
from motor.motor_asyncio import AsyncIOMotorClient
from ..core.config import settings

class Database:
    client: AsyncIOMotorClient = None


db = Database()


async def get_database() -> AsyncIOMotorClient:
    return db.client


async def connect():
    """Connect to MONGO DB
    """
    db.client = AsyncIOMotorClient(str(settings.MDB_URI),
                                   maxPoolSize=settings.MAX_CONNECTIONS_COUNT,
                                   minPoolSize=settings.MIN_CONNECTIONS_COUNT)
    print(f"Connected to mongo at {settings.MDB_URI}")


async def close():
    """Close MongoDB Connection
    """
    db.client.close()
    print("Closed connection with MongoDB")