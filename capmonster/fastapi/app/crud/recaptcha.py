"""
CRUD Operations for ReCaptcha
"""
from typing import Optional, List, Union
import datetime
from datetime import timezone
import secrets
from bson import ObjectId
from fastapi.encoders import jsonable_encoder
from pydantic import EmailStr
from pymongo import DeleteOne

from app.db.mongodb import AsyncIOMotorClient
from app.schema.recaptcha import ReCaptchaResponse, ReCaptchaCreate, ReCaptchaInDb, ReCaptchaSolved, ReCaptchaInCreate
from app.core.config import settings


async def total_docs_in_db(conn: AsyncIOMotorClient) -> int:
    """Get total documents in the database
    :param conn: AsyncIOMotorClient connection
    :return: INT count of the total docs in mongodb or 0 if none
    """
    return await conn[settings.MDB_DATABASE][settings.MDB_COLLECTION].count_documents({})


async def get_one_recaptcha(conn: AsyncIOMotorClient) -> ReCaptchaResponse:
    """

    """
    one = await conn[settings.MDB_DATABASE][settings.MDB_COLLECTION].find_one({})
    return ReCaptchaResponse(**one)


async def get_all_recaptcha(conn: AsyncIOMotorClient) -> List[ReCaptchaResponse]:
    """

    """
    rsp = []
    print(settings.MDB_URI)
    print(settings.MDB_COLLECTION)
    all = conn[settings.MDB_DATABASE][settings.MDB_COLLECTION].find({})
    async for a in all:
        rsp.append(ReCaptchaResponse(**a))
    return rsp


async def create_recaptcha(conn: AsyncIOMotorClient, recaptcha: ReCaptchaCreate) -> ReCaptchaInDb:
    """ Add recaptcha job to the DB

    """
    # Add DateTime
    recaptcha = ReCaptchaInCreate(**recaptcha.dict())
    recaptcha_doc = jsonable_encoder(recaptcha)
    new_recaptcha = await conn[settings.MDB_DATABASE][settings.MDB_COLLECTION].insert_one(recaptcha_doc)
    created_recaptcha = await conn[settings.MDB_DATABASE][settings.MDB_COLLECTION].find_one({"_id": new_recaptcha.inserted_id})

    return ReCaptchaInDb(**created_recaptcha)


async def get_recaptcha(conn: AsyncIOMotorClient, job_id: ObjectId) -> Union[ReCaptchaResponse, ReCaptchaSolved, None]:
    """ Retrieve a captcha job from the DB
    """
    result = await conn[settings.MDB_DATABASE][settings.MDB_COLLECTION].find_one({"_id": job_id})
    if not result:
        return None
    if 'solution' in result.keys():
        return ReCaptchaSolved(**result)
    return ReCaptchaResponse(**result)


async def purge_garbage(conn: AsyncIOMotorClient) -> int:
    all = conn[settings.MDB_DATABASE][settings.MDB_COLLECTION].find({})
    updates = []
    async for document in all:
        if "created_on" in document.keys():
            created_on = document['created_on']

            if isinstance(document['created_on'], str):
                created_on = datetime.datetime.fromisoformat(document['created_on'].replace("Z", "+00:00")).replace(tzinfo=timezone.utc)
            elif isinstance(document['created_on'], datetime.datetime):
                created_on = (document['created_on']).replace(tzinfo=timezone.utc)
            else:
                raise TypeError
            if ((datetime.datetime.now(timezone.utc) - created_on).total_seconds() / 60) >= settings.GARBAGE_TIMER:
                updates.append(DeleteOne({'_id': document["_id"]}))

    if updates:
        # await conn.bulk_write(updates)
        print(f"Garbage collection purged {len(updates)} documents from the database")
        return len(updates)
    return 0