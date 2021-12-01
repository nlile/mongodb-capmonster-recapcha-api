import logging
from datetime import datetime
from typing import Union
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection
import httpx
import asyncio
import os
from dotenv import find_dotenv, load_dotenv
from mdb import MongoDB
from capmonster.fastapi.app.schema.recaptcha import ReCaptchaCreate, ReCaptchaResponse, ReCaptchaSolved, ReCaptchaInDb, \
    ReCaptchaErrorResponse
from capmonster.fastapi.app.schema.common import ProxyTypeEnum

"""
    Logic for GET/POST requests using 2Captcha API style
"""

# Load env
load_dotenv(find_dotenv())
TEST_PROXY: str = str(os.getenv("TEST_PROXY"))
TEST_GOOGLEKEY: str = str(os.getenv("TEST_GOOGLEKEY"))
TEST_URL: str = str(os.getenv("TEST_URL"))

# List of critical errors that prevent the job from being re-tried
CRITICAL_ERRORS = [
    "ERROR_RECAPTCHA_INVALID_SITEKEY",
    "ERROR_BAD_PARAMETERS",
    "ERROR_WRONG_USER_KEY",
    "ERROR_KEY_DOES_NOT_EXIST",
    "ERROR_WRONG_ID_FORMAT",
]

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class CaptchaError(Exception):
    """Raised when error solving captcha"""

    def __init__(self, message="Error solving captcha.", *args, **kwargs):
        self.message = message
        super().__init__(self.message)


class ReCaptchaError(CaptchaError):
    """Raised when error solving recaptcha"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args)
        self.text = kwargs.get('text')


class CaptchaUpload:
    """
    Manages 2captcha API requests (Intercepted locally by CapMonster)
    """

    def __init__(self, collection: AsyncIOMotorCollection,
                 key: str = None, waittime: int = None, log=None):

        self.collection = collection
        # self.key = key if key is not None else os.getenv("ROOT_API_KEY")
        self.key = key or os.getenv("ROOT_API_KEY")
        self.first_waittime = waittime or int(os.getenv("CLIENT_INIT_SLEEP"))
        self.waittime = int(os.getenv("CLIENT_RETRY_SLEEP")) or 5
        self.timeout = int(os.getenv("HTTPX_TIMEOUT")) or 120
        if log:
            self.log = log
            self.logenabled = True
        else:
            self.logenabled = False

        # 2CaptchaAPI endpoints
        # CapMonster intercepts DNS for 2captcha.com
        self.api: dict = {
            "url_request": "http://2captcha.com/in.php",
            "post": "http://2captcha.com/in.php",
            "url_response": "http://2captcha.com/res.php",
            "get": "http://2captcha.com/res.php",
        }

    async def get_result(self, cap_id) -> str:
        """
        This function checks for CapMonster status/completion and returns the result from CapMonster.
        If CapMonster fails to solve, will raise an error
        :param cap_id: id of the uploaded ReCaptcha job
        :return: Captcha solution string
        """
        if self.logenabled:
            self.log.info(f"[CapMonster] Wait {self.waittime} second..")
        await asyncio.sleep(self.waittime)

        fullurl = f"{self.api['get']}?key={self.key}&action=get&id={cap_id}"
        # logger.info(fullurl)

        if self.logenabled:
            self.log.info(f"[CapMonster] Get Captcha solved with cap_id {cap_id}")
        async with httpx.AsyncClient() as client:
            request = await client.get(fullurl, timeout=self.timeout)
            # logger.info(f"Request: {request}\t{request.text}")
            if request.text.split('|')[0] == "OK":
                return request.text.split('|')[1]
            elif request.text == "CAPCHA_NOT_READY":
                if self.logenabled:
                    self.log.error(f"[CapMonster] [{cap_id}] CAPTCHA is being solved, "
                                   "repeat the request several seconds later, wait "
                                   f"another {self.waittime} seconds")
                return await self.get_result(cap_id)

            # ERROR Responses
            elif request.text == "ERROR_KEY_DOES_NOT_EXIST":
                if self.logenabled:
                    self.log.error("[CapMonster] You used the wrong key in the query")
                raise ReCaptchaError('[CapMonster] You used the wrong key in the query', text=request.text)

            elif request.text == "ERROR_WRONG_ID_FORMAT":
                if self.logenabled:
                    self.log.error("[CapMonster] Wrong format ID CAPTCHA.\nID must contain only numbers")
                raise ReCaptchaError('[CapMonster] Wrong format ID CAPTCHA.\nID must contain only numbers.',
                                     text=request.text)

            elif request.text == "ERROR_CAPTCHA_UNSOLVABLE":
                if self.logenabled:
                    self.log.error("[CapMonster] After three attempts the captcha was still unsolved.")
                raise ReCaptchaError('[CapMonster] After three attempts the captcha was still unsolved.',
                                     text=request.text)

            elif "ERROR_RECAPTCHA_TIMEOUT" in request.text:
                if self.logenabled:
                    self.log.error("[CapMonster] TimeOut error, probably a bad proxy.")
                raise ReCaptchaError('[CapMonster] TimeOut error, probably a bad proxy.',
                                     text=request.text)

            elif "ERROR_PROXY_BANNED" in request.text:
                if self.logenabled:
                    self.log.error("[CapMonster] Your proxy is banned and cannot be used to solve the recaptcha.")
                raise ReCaptchaError('[CapMonster] Proxy is banned.',
                                     text=request.text)
            elif "ERROR_PROXY_FORMAT" == request.text:
                if self.logenabled:
                    self.log.error("[CapMonster] Malformed proxy format")
                raise ReCaptchaError('[CapMonster] Malformed proxy format', text=request.text)
            elif "ERROR" == request.text:
                if self.logenabled:
                    self.log.error("[CapMonster] Error message simply 'ERROR', likely malformed URL")
                raise ReCaptchaError('[CapMonster] Error message simply "Error"', text=request.text)
            elif "ERROR_RECAPTCHA_INVALID_SITEKEY" == request.text:
                if self.logenabled:
                    self.log.error("[CapMonster] SITEKEY Authentication is Invalid")
                raise ReCaptchaError('[CapMonster] SITEKEY Authentication is Invalid', text=request.text)
            else:
                if self.logenabled:
                    self.log.error(f"[CapMonster] Unexpected error response type: {request.text}")
                    self.log.error(f"{request}")
                raise ReCaptchaError(f'[CapMonster] Unexpected error response type: {request.text}.',
                                     text=request.text)

    async def solve_recaptcha(self, recapcha: Union[ReCaptchaCreate, ReCaptchaInDb]) -> Union[ReCaptchaSolved, ReCaptchaErrorResponse]:
        """
        The function to handle, upload, solve, and update a recaptcha
        :param recapcha: Pydantic instance of either ReCaptchaCreate or ReCaptchaInDb.
        :return: The ReCaptchaSolved object that was written to the CloudDB
        """
        if recapcha.googlekey and recapcha.pageurl and 'http' in recapcha.pageurl:
            full_url = f"{self.api['post']}?key={self.key}&method={recapcha.method}&googlekey={recapcha.googlekey}&pageurl={recapcha.pageurl}"
            if recapcha.proxy and recapcha.proxytype:
                full_url = f"{full_url}&proxy={recapcha.proxy}&proxytype={recapcha.proxytype}"
            elif recapcha.proxy:
                # Assume HTTP proxy by default
                full_url = f"{full_url}&proxy={recapcha.proxy}&proxytype=HTTP"
            logger.info(full_url)
            # If type ReCaptchaCreate, job is not yet in DB with valid cap_id
            if type(recapcha) == ReCaptchaCreate:
                if self.logenabled:
                    self.log.info(f"Model is ReCaptchaCreate and does not have an _id, adding new DB entry")
                captcha_job = await self.collection.insert_one(recapcha.dict(exclude_none=True))
                _id = captcha_job.inserted_id
            else:
                _id = recapcha.id
            if self.logenabled:
                self.log.info(f"Working on _id {_id}")
            if self.logenabled:
                self.log.info(f"[CapMonster] Built url: {full_url} for DB _id {_id}")
            async with httpx.AsyncClient() as client:
                request = await client.post(full_url, timeout=self.timeout)
                if request.text:
                    if request.text.split('|')[0] == "OK":
                        if self.logenabled:
                            self.log.info("[CapMonster] Upload Ok")
                        # Received Job ID
                        job_id = request.text.split('|')[1]
                        recapcha_upload = ReCaptchaResponse(captcha_id=job_id, **recapcha.dict())

                        # Previously used exclude={"captcha_id"} because client.py used this as the job identifier
                        # Since switched to ObjectId which does not change when SOLVE_ATTEMPTS > 1
                        await self.collection.update_one({"_id": ObjectId(_id)},
                                                         {"$set": recapcha_upload.dict(exclude_none=True)}
                                                         )
                        try:
                            await asyncio.sleep(self.first_waittime)
                            solution = await self.get_result(job_id)
                        except ReCaptchaError as rce:
                            logger.error(f"{rce.message}\t{rce.text}")
                            if any(rce.text == critical_error for critical_error in CRITICAL_ERRORS):
                                recapcha_error = ReCaptchaErrorResponse(finished_on=datetime.now(),
                                                                   error=rce.text,
                                                                   **recapcha_upload.dict(exclude_none=True,
                                                                                          exclude={"cap_id"}))
                                await self.collection.update_one({"_id": ObjectId(_id)},
                                                                 {"$set": recapcha_error.dict(exclude_none=True,
                                                                                              exclude={"cap_id"})})
                                return recapcha_error
                            raise

                        recapcha_answer = ReCaptchaSolved(solution=solution, finished_on=datetime.now(),
                                                          **recapcha_upload.dict(exclude_none=True, exclude={"cap_id"}))
                        await self.collection.update_one({"_id": ObjectId(_id)},
                                                         {"$set": recapcha_answer.dict(exclude_none=True,
                                                                                       exclude={"cap_id"})}
                                                         )
                        return recapcha_answer

                    elif request.text == "ERROR_WRONG_USER_KEY":
                        if self.logenabled:
                            self.log.error(
                                "[CapMonster] Wrong 'key' parameter format, it should contain 32 symbols")
                        raise ReCaptchaError(f'[CapMonster] {request.text}', text=request.text)
                    elif request.text == "ERROR_KEY_DOES_NOT_EXIST":
                        if self.logenabled:
                            self.log.error("[CapMonster] The 'key' doesn't exist")
                        raise ReCaptchaError(f'[CapMonster] {request.text}', text=request.text)
                    elif request.text == "ERROR_ZERO_BALANCE":
                        if self.logenabled:
                            self.log.error("[CapMonster] Your account balance is empty.")
                        raise ReCaptchaError(f'[CapMonster] {request.text}', text=request.text)
                    elif request.text == "ERROR_NO_SLOT_AVAILABLE":
                        if self.logenabled:
                            self.log.error("[CapMonster] The current bid is higher than the maximum bid set for "
                                           "your account.")
                        raise ReCaptchaError(f'[CapMonster] {request.text}', text=request.text)
                    elif request.text == "ERROR_ZERO_CAPTCHA_FILESIZE":
                        if self.logenabled:
                            self.log.error("[CapMonster] CAPTCHA size is too small (less than 100 bites)")
                        raise ReCaptchaError(f'[CapMonster] {request.text}', text=request.text)
                    elif request.text == "ERROR_TOO_BIG_CAPTCHA_FILESIZE":
                        if self.logenabled:
                            self.log.error("[CapMonster] CAPTCHA size is too large (is more than 100kb)")
                        raise ReCaptchaError(f'[CapMonster] {request.text}', text=request.text)
                    elif request.text == "ERROR_WRONG_FILE_EXTENSION":
                        if self.logenabled:
                            self.log.error("[CapMonster] The CAPTCHA has a wrong extension. Allowed extensions "
                                           "are: jpg,jpeg,gif,png")
                        raise ReCaptchaError(f'[CapMonster] {request.text}', text=request.text)
                    elif request.text == "ERROR_IMAGE_TYPE_NOT_SUPPORTED":
                        if self.logenabled:
                            self.log.error("[CapMonster] The server cannot recognize the CAPTCHA file type."
                                           "Allowed extensions are: jpg,jpeg,gif,png")
                        raise ReCaptchaError(f'[CapMonster] {request.text}', text=request.text)
                    elif request.text == "ERROR_IP_NOT_ALLOWED":
                        if self.logenabled:
                            self.log.error("[CapMonster] The request has sent "
                                           "from the IP that is not on the list of"
                                           " your IPs.")
                        raise ReCaptchaError(f'[CapMonster] {request.text}', text=request.text)
                    elif request.text == "IP_BANNED":
                        if self.logenabled:
                            self.log.error("[CapMonster] The IP address you're"
                                           " trying to access the server with is "
                                           "banned due to many frequent attempts "
                                           "to access the server using wrong "
                                           "authorization keys.")
                        raise ReCaptchaError(f'[CapMonster] {request.text}', text=request.text)
                else:
                    logger.error("BAD REQUEST")
                    raise ReCaptchaError(f'[CapMonster] BAD REQUEST', text="BAD REQUEST")
        else:
            if self.logenabled:
                self.log.error("[CapMonster] One or more parameters was incorrect")
            raise ReCaptchaError(f'[CapMonster] One or more parameters was incorrect',
                                 text="One or more parameters was incorrect")


async def test_captcha_solver():
    """
    Tests solve_recaptcha()
    """
    db = MongoDB()
    collection = await db.get_collection()
    captcha = CaptchaUpload(collection, log=logging.getLogger(__name__))

    # Use test/example fields
    x = ReCaptchaCreate(pageurl=TEST_URL, googlekey=TEST_GOOGLEKEY, proxy=TEST_PROXY, proxytype=ProxyTypeEnum["http"],
                        api_key=captcha.key)
    attempts = 3
    while True:
        if 0 > attempts:
            break
        try:
            attempts -= 1
            result = await captcha.solve_recaptcha(x)
            break
        except TimeoutError:
            continue
        except ReCaptchaError as rce:
            if "ERROR_RECAPTCHA_TIMEOUT" in rce.text:
                continue
            if "banned" in rce.text.lower():
                await asyncio.sleep(10)
                continue
            quit(1)


if __name__ == "__main__":
    logger.info("Running test function")
    asyncio.run(test_captcha_solver())
