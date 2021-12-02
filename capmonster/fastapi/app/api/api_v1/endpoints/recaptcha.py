from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Any, Union, Optional
from pydantic import ValidationError
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure
from fastapi.responses import PlainTextResponse

from app.core.config import settings
from app.core.utils import create_aliased_response
from app.crud.api_key import get_api_key, subtract_credit
from app.crud.recaptcha import get_one_recaptcha, get_all_recaptcha, create_recaptcha, get_recaptcha, purge_garbage
from app.db.mongodb import AsyncIOMotorClient, get_database
from app.schema.common import PyObjectId
from app.schema.recaptcha import ReCaptchaResponse, ReCaptchaInDb, ReCaptchaCreate, ReCaptchaSolved, \
    ReCaptchaResponse2Captcha

""" 
Error codes hard-coded from: https://2captcha.com/2captcha-api#error_handling
"""

router = APIRouter(tags=["recaptcha"],)


@router.get("/", response_model=str)
async def database_status(
        db: AsyncIOMotorClient = Depends(get_database), ) -> Any:
    """
    Checks if the database is online and returns the server version.
    """
    try:
        server_info = await db.server_info()
        return f"Database Version: {server_info['version']}"
    except ServerSelectionTimeoutError as sste:
        return f"MongoDB Error: {sste}"
    except ConnectionFailure as cf:
        return f"MongoDB Server Unavailable: {cf}"
    except Exception as e:
        return f"Unknown MongoDB Exception: {e}"


@router.get("/garbage", response_model=int)
async def garbage_collection(
        db: AsyncIOMotorClient = Depends(get_database), ) -> int:
    """
    Purges expired documents from the database based on settings GARBAGE_TIMER.
    """
    return await purge_garbage(db)


@router.post("/submit", response_model=ReCaptchaInDb,
             response_model_exclude_unset=True, response_model_exclude_none=True)
async def submit_recaptcha(recaptcha: ReCaptchaCreate,
                           db: AsyncIOMotorClient = Depends(get_database), ):
    """
    Create new ReCaptcha job.
    """
    validate_key = await get_api_key(db, apikey=recaptcha.api_key)
    if validate_key:
        if validate_key.credits < 1:
            return PlainTextResponse("ERROR_ZERO_BALANCE", status_code=401)

    if not validate_key and recaptcha.api_key != settings.ROOT_API_KEY:
        raise HTTPException(
            status_code=401,
            detail=f"API Key not authorized",
        )
    result = await create_recaptcha(db, recaptcha)
    if result and validate_key:
        subtracted = await subtract_credit(db, apikey=validate_key.key)
    return result


@router.get("/2captcha", response_class=PlainTextResponse)
async def get_recaptcha_job_2captcha(key: str,
                                     job_id: PyObjectId = Query(..., alias="id"),
                                     action: str = "get",
                                     db: AsyncIOMotorClient = Depends(get_database), ):
    """
    Mimic 2Captcha API endpoint parameters to retrieve a ReCaptcha job by job_id.
    """
    if key != settings.ROOT_API_KEY:
        return PlainTextResponse("ERROR_WRONG_USER_KEY", status_code=401)

    job = await get_recaptcha(db, ObjectId(job_id))
    # The job_id does not exist in the database, return ERROR_WRONG_CAPTCHA_ID
    if not job:
        return PlainTextResponse("ERROR_WRONG_CAPTCHA_ID", status_code=404)

    # The job is finished if the solution exists
    s = getattr(job, "solution", None)
    if s is not None:
        return f"OK|{s}"

    # If a job is in_queue without a solution, it is still processing
    q = getattr(job, "in_queue", None)
    if q:
        return "CAPCHA_NOT_READY"

    # If the job contains an error code/message, return it
    err = getattr(job, "error", None)
    if err is not None:
        return PlainTextResponse(str(job.error), status_code=400)

    # The job has a finished_on timestamp indicating finished, but no solution
    f = getattr(job, "finished_on", None)
    if f:
        return PlainTextResponse("ERROR_CAPTCHA_UNSOLVABLE", status_code=408)

    # The Local CapMonster script has not yet received the captcha job
    c = getattr(job, "captcha_id", None)
    if not c and not f:
        # TODO: Check created_on delta
        return PlainTextResponse("CAPCHA_NOT_READY", status_code=425)

    # Unhandled error
    return PlainTextResponse("ERROR_CAPTCHA_UNSOLVABLE", status_code=418)


@router.post("/2captcha/submit", response_class=PlainTextResponse)
async def submit_recaptcha_2captcha(key: str,
                                    googlekey: str,
                                    pageurl: str,
                                    method: str = "userrecaptcha",
                                    proxy: Optional[str] = None,
                                    proxytype: Optional[str] = None,
                                    json: int = 0,
                                    db: AsyncIOMotorClient = Depends(get_database), ):
    """
    Mimic 2Captcha API endpoint parameters to create a new ReCaptcha job.
    """
    validate_key = await get_api_key(db, apikey=key)
    if validate_key:
        if validate_key.credits < 1:
            return PlainTextResponse("ERROR_ZERO_BALANCE", status_code=401)
    if not validate_key and key != settings.ROOT_API_KEY:
        return PlainTextResponse("ERROR_WRONG_USER_KEY", status_code=401)
    try:
        proxytype = proxytype.upper() if proxytype else None
        recaptcha = ReCaptchaCreate(api_key=key, method=method, googlekey=googlekey, pageurl=pageurl, proxy=proxy,
                                    proxytype=proxytype)
        result = await create_recaptcha(db, recaptcha)
        if result and validate_key:
            subtracted = await subtract_credit(db, apikey=validate_key.key)
        if json == 0:
            return f"OK|{result.id}"
        return {"status": 1, "request": f"{result.id}"}
    except ValidationError as ve:
        return PlainTextResponse("ERROR_BAD_PARAMETERS", status_code=422)
    except Exception as e:
        return PlainTextResponse(f"UNKNOWN_ERROR: {e}", status_code=422)


@router.get("/{job_id}", response_model=Union[ReCaptchaResponse, ReCaptchaSolved],
            response_model_exclude_unset=True, response_model_exclude_none=True)
async def get_recaptcha_job(job_id: PyObjectId,
                            db: AsyncIOMotorClient = Depends(get_database), ):
    """
    Retrieve ReCaptcha job by job_id.
    """
    print(job_id)
    print(type(job_id))
    job = await get_recaptcha(db, ObjectId(job_id))
    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Job with id '{job_id}' not found",
        )
    return create_aliased_response(job)
