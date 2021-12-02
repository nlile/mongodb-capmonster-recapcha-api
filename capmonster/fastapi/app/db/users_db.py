import motor
from fastapi import Depends
from fastapi_users import models
from fastapi_users.db import MongoDBUserDatabase
from motor.motor_asyncio import AsyncIOMotorClient

from app.schema.user import UserDB
from app.core.config import settings

user_client = motor.motor_asyncio.AsyncIOMotorClient(
    str(settings.MDB_URI)
)
collection = user_client[settings.MDB_DATABASE][settings.MDB_COLLECTION_USERS]


async def get_user_db():
    yield MongoDBUserDatabase(UserDB, collection)

