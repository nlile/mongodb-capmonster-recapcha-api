from fastapi.encoders import jsonable_encoder
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Union

from app.core.config import settings
from app.schema.api_key import APIKeyCaptchaCreate, APIKeyCaptchaBase, APIKeyCaptchaInResponse


async def create_api_key(conn: AsyncIOMotorClient, apikey: APIKeyCaptchaBase) -> APIKeyCaptchaInResponse:
    """

    """
    # Add DateTime
    new_apikey = APIKeyCaptchaCreate(**apikey.dict())
    new_apikey_doc = jsonable_encoder(new_apikey)
    inserted_apikey = await conn[settings.MDB_DATABASE][settings.MDB_COLLECTION_KEYS].insert_one(new_apikey_doc)
    created_apikey = await conn[settings.MDB_DATABASE][settings.MDB_COLLECTION_KEYS].find_one(
        {"_id": inserted_apikey.inserted_id})
    return APIKeyCaptchaInResponse(**created_apikey)


async def get_api_key(conn: AsyncIOMotorClient, apikey: str = None, user_id: str = None) -> Union[APIKeyCaptchaInResponse, None]:
    if not apikey and not user_id:
        return None
    if apikey:
        query = {"key": apikey}
    else:
        query = {"user": user_id}

    found_key = await conn[settings.MDB_DATABASE][settings.MDB_COLLECTION_KEYS].find_one(query)
    if not found_key:
        return None
    return APIKeyCaptchaInResponse(**found_key)


async def subtract_credit(conn: AsyncIOMotorClient, apikey: str = None, user_id: str = None) -> None:
    if apikey:
        query = {"key": apikey}
    else:
        query = {"user": user_id}
    updated_key = await conn[settings.MDB_DATABASE][settings.MDB_COLLECTION_KEYS].update_one(query,
                                                                                         {"$inc": {"credits": -1}})
