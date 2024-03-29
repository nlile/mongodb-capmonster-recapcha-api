import asyncio
import os
from pprint import pprint
import httpx
from bson import ObjectId
from dotenv import load_dotenv, find_dotenv
from motor.motor_asyncio import AsyncIOMotorCollection

import sys
from pathlib import Path
# Grab and append root path for imports
fastpath = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(fastpath))
from mdb import MongoDB
from capmonster.fastapi.app.schema.recaptcha import ProxyTypeEnum, ReCaptchaCreate

"""
    Example of a client script to request and wait for ReCaptcha solves from server.py
"""

# Load env
load_dotenv(find_dotenv())
TEST_PROXY: str = str(os.getenv("TEST_PROXY"))
TEST_GOOGLEKEY: str = str(os.getenv("TEST_GOOGLEKEY"))
TEST_URL: str = str(os.getenv("TEST_URL"))
ROOT_API_KEY: str = str(os.getenv("ROOT_API_KEY"))

# Uses same sleep settings as the captcha_solver get result
INITIAL_WAIT: int = int(os.getenv("CLIENT_INIT_SLEEP")) or 3
RETRY_WAIT: int = int(os.getenv("CLIENT_RETRY_SLEEP")) or 3

# Set timeout to max possible time
HTTP_TIMEOUT: int = int(os.getenv("HTTPX_TIMEOUT")) or 120
SOLVE_ATTEMPTS: int = int(os.getenv("SOLVE_ATTEMPTS")) or 3
HIT_DB_DELAY: int = int(os.getenv("HIT_DB_DELAY")) or 3
# A starting-point estimation for TIMEOUT. This number should be SOLVE_ATTEMPTS * average solve-time + some change.
# You should definitely increase this if you're using low quality proxies (2-3x)
TIMEOUT: int = int((HTTP_TIMEOUT * SOLVE_ATTEMPTS) + (HIT_DB_DELAY * 2))


class CaptchaSolveError(Exception):
    """Raised when error solving captcha"""
    def __init__(self, message="Error solving captcha.", *args, **kwargs):
        self.message = message
        super().__init__(self.message)


async def check_for_solution_local(mdb_id: ObjectId, collection: AsyncIOMotorCollection) -> str:
    """
    Loops for max-time waiting for a solution (finished result) in the MongoDB
    Non-local scripts call this function instead of a captcha_solver.py function
    """
    # Loop through the max number of times that 3x timeouts could take
    for _ in range(int(TIMEOUT / RETRY_WAIT)):
        result = await collection.find_one({"_id": mdb_id})
        # Solution indicates the job is fully finished
        if "solution" in result.keys():
            print(f"Finished!\n{result['solution']}")
            return result["solution"]
        # Error indicates the job finished max retries with an error
        if "error" in result.keys():
            raise CaptchaSolveError(message=result["error"])
        await asyncio.sleep(RETRY_WAIT)
    raise TimeoutError


async def check_for_solution_fastapi(mdb_id: str, fastapi_endpoint_url: str) -> str:
    """

    """
    # Captcha solving takes time, initial wait of 30 seconds
    await asyncio.sleep(25)
    # Loop through the max number of times that 3x timeouts could take
    for _ in range(int(TIMEOUT / RETRY_WAIT)):
        await asyncio.sleep(RETRY_WAIT)

        fullurl = f"{fastapi_endpoint_url}?key={ROOT_API_KEY}&action=get&id={mdb_id}"
        print(f"[2CaptchaUpload] Get Captcha with id {mdb_id}")
        async with httpx.AsyncClient() as client:
            request = await client.get(fullurl, timeout=60)
            print(request.text)

            # Ensure captcha is solved before returning key or errors
            while request.text == "CAPCHA_NOT_READY":
                await asyncio.sleep(RETRY_WAIT)
                request = await client.get(fullurl, timeout=60)
                print(request.text)

            if request.text.split('|')[0] == "OK":
                return request.text.split('|')[1]
            else:
                print("Handle response errors here")
                raise CaptchaSolveError

    raise TimeoutError


async def submit_job(collection: AsyncIOMotorCollection,
                     pageurl: str,
                     googlekey: str,
                     proxy: str = None,
                     proxytype: ProxyTypeEnum = ProxyTypeEnum["http"],
                     api_key: str = "NOTNEEDED") -> ObjectId:
    """
    Submits the job requirements to the MongoDB Atlas
    """
    recapcha = ReCaptchaCreate(pageurl=pageurl, googlekey=googlekey, proxy=proxy, proxytype=proxytype, api_key=api_key)
    captcha_job = await collection.insert_one(recapcha.dict(exclude_none=True))
    return captcha_job.inserted_id


async def get_captcha_answer(pageurl: str,
                             googlekey: str,
                             proxy: str = None,
                             proxytype: ProxyTypeEnum = ProxyTypeEnum["http"],
                             api_key: str = "NOTNEEDED") -> str:
    """
    Function for handling submitting, checking, and returning the answer to a recaptcha
    :param pageurl: Page URL with the Recaptcha
    :param googlekey: The Google Recaptcha ID Key
    :param proxy: Proxy
    :param proxytype: Proxy type enum
    :param api_key: API Key for subscription/paid 2captcha service
    :return: The string answer to the recaptcha
    """
    db = MongoDB()
    collection = await db.get_collection()
    job_id = await submit_job(collection, pageurl=pageurl, googlekey=googlekey,
                              proxy=proxy, proxytype=proxytype, api_key=api_key)
    print(f"Job added, giving CapMonster some time to work by sleeping for {INITIAL_WAIT}")
    await asyncio.sleep(INITIAL_WAIT)
    try:
        return await check_for_solution_local(job_id, collection)
    except TimeoutError:
        raise
    except Exception as e:
        print(e)
        raise


async def client_example_local():
    """
    Client example / test for running /capmonster/local/ WITHOUT fastapi
    """
    db = MongoDB()
    collection = await db.get_collection()

    recapcha = ReCaptchaCreate(api_key=ROOT_API_KEY, pageurl=TEST_URL, googlekey=TEST_GOOGLEKEY,
                               proxy=TEST_PROXY, proxytype=ProxyTypeEnum["http"])

    captcha_job = await collection.insert_one(recapcha.dict(exclude_none=True))
    print(f"Hold on to {captcha_job.inserted_id} and query DB to check if updated")
    await asyncio.sleep(INITIAL_WAIT)
    await check_for_solution_local(ObjectId(captcha_job.inserted_id), collection)


async def client_example_fastapi(fastapi_endpoint_url: str):
    """
    Client example / test for running /capmonster/local/ WITH fastapi
    """
    fullurl = f"{fastapi_endpoint_url}/submit?key={ROOT_API_KEY}&method=userrecaptcha&googlekey={TEST_GOOGLEKEY}&pageurl={TEST_URL}&proxy={TEST_PROXY}&proxytype=HTTP"

    print(fullurl)
    async with httpx.AsyncClient() as client:
        request = await client.post(fullurl, timeout=60)
        if request.status_code:
            pprint(request.status_code)
            if request.text.split('|')[0] == "OK":
                print("[2CaptchaUpload] Upload Ok\n", request.text.split('|')[1])
                return await check_for_solution_fastapi(request.text.split('|')[1], fastapi_endpoint_url)
            else:
                print("Handle errors here")



## Quick Test
if __name__ == "__main__":
    asyncio.run(client_example_fastapi("https://api.middleware.link/api/v1/2captcha"))
    # asyncio.run(client_example_local())
