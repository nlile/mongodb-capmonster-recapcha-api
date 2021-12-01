from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from typing import Any, List, Union, Optional

from pydantic import ValidationError
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure
from starlette.responses import JSONResponse

from app.core.config import settings
from app.core.utils import create_aliased_response
from app.crud.recaptcha import get_one_recaptcha, get_all_recaptcha, create_recaptcha, get_recaptcha, purge_garbage
from app.db.mongodb import AsyncIOMotorClient, get_database
from app.schema.common import PyObjectId
from fastapi.responses import PlainTextResponse
from app.schema.recaptcha import ReCaptchaResponse, ReCaptchaInDb, ReCaptchaCreate, ReCaptchaSolved, \
    ReCaptchaResponse2Captcha

""" Error codes hard-coded from: https://2captcha.com/2captcha-api#error_handling
"""

router = APIRouter()


@router.get("/", response_model=str)
async def operation_status(
        db: AsyncIOMotorClient = Depends(get_database), ) -> Any:
    try:
        return f"Server Response: {db.server_info()}"
    except ServerSelectionTimeoutError as sste:
        return f"MongoDB Error: {sste}"
    except ConnectionFailure as cf:
        return f"MongoDB Server Unavailable: {cf}"
    except Exception as e:
        return f"Unknown Exception: {e}"


@router.get("/garbage", response_model=int)
async def remove_garbage(
        db: AsyncIOMotorClient = Depends(get_database), ):
    return await purge_garbage(db)


@router.post("/submit", response_model=ReCaptchaInDb,
             response_model_exclude_unset=True, response_model_exclude_none=True)
async def post_captcha(recaptcha: ReCaptchaCreate,
                 db: AsyncIOMotorClient = Depends(get_database), ):
    if recaptcha.api_key != settings.ROOT_API_KEY:
        raise HTTPException(
            status_code=401,
            detail=f"API Key not authorized",
        )
    return await create_recaptcha(db, recaptcha)


@router.get("/{job_id}", response_model=Union[ReCaptchaResponse, ReCaptchaSolved],
            response_model_exclude_unset=True, response_model_exclude_none=True)
async def get_job_id(job_id: PyObjectId,
                     db: AsyncIOMotorClient = Depends(get_database), ):
    job = await get_recaptcha(db, ObjectId(job_id))
    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Job with id '{job_id}' not found",
        )
    return create_aliased_response(job)


@router.post("/2captcha/submit", response_class=PlainTextResponse)
async def post_as_2captcha(key: str,
                           googlekey: str,
                           pageurl: str,
                           method: str = "userrecaptcha",
                           proxy: Optional[str] = None,
                           proxytype: Optional[str] = None,
                           json: int = 0,
                           db: AsyncIOMotorClient = Depends(get_database), ):
    if key != settings.ROOT_API_KEY:
        return PlainTextResponse("ERROR_WRONG_USER_KEY", status_code=401)
    try:
        recaptcha = ReCaptchaCreate(api_key=key, method=method, googlekey=googlekey, pageurl=pageurl, proxy=proxy,
                                    proxytype=proxytype)
        result = await create_recaptcha(db, recaptcha)
        if json == 0:
            return f"OK|{result.id}"
        return {"status": 1, "request": f"{result.id}"}
    except ValidationError:
        return PlainTextResponse("ERROR_BAD_PARAMETERS", status_code=422)
    except Exception as e:
        return PlainTextResponse(f"UNKNOWN_ERROR: {e}", status_code=422)


@router.get("/2captcha/{job_id}", response_class=PlainTextResponse)
async def get_job_id(job_id: PyObjectId,
                     db: AsyncIOMotorClient = Depends(get_database), ):
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
