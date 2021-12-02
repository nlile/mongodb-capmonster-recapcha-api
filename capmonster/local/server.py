import asyncio
import logging
import os
import random
import datetime
from datetime import timezone
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import UpdateOne, DeleteOne
from pymongo.errors import ServerSelectionTimeoutError
from dotenv import load_dotenv, find_dotenv
import sys
from pathlib import Path
# Grab and append root path for imports
fastpath = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(fastpath))
from captcha_solver import CaptchaUpload, ReCaptchaError
from mdb import MongoDB
from capmonster.fastapi.app.schema.recaptcha import ReCaptchaInDb

"""
    Infinite async producer/consumer loop that runs on the Windows computer with CapMonster
    
    Listens for CloudDB updates, passes the requests to CapMonster, and updates the DB once finished
"""

# Load env for Windows server script
load_dotenv(find_dotenv())
HIT_DB_SLEEP: int = int(os.getenv("HIT_DB_DELAY")) or 3
SERVER_WORKERS: int = int(os.getenv("SERVER_WORKERS")) or 3
GARBAGE_TIMER: int = int(os.getenv("GARBAGE_TIMER")) or (60 * 24)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


async def purge_garbage(collection: AsyncIOMotorCollection):
    """
    Purges documents older than GARBAGE_TIMER
    Can implement here or via cron/scheduled FastAPI endpoints
    """
    updates = []
    all_documents = collection.find({})
    async for document in all_documents:
        if "created_on" in document.keys():
            created_on = document['created_on']
            if isinstance(document['created_on'], str):
                created_on = datetime.datetime.fromisoformat(document['created_on'].replace(
                    "Z", "+00:00")).replace(tzinfo=timezone.utc)
            elif isinstance(document['created_on'], datetime.datetime):
                created_on = (document['created_on']).replace(tzinfo=timezone.utc)
            else:
                raise TypeError
            if ((datetime.datetime.now(timezone.utc) - created_on).total_seconds() / 60) >= GARBAGE_TIMER:
                logger.info(f"Time delta: {(datetime.datetime.now(timezone.utc) - created_on).total_seconds() / 60}")
                updates.append(DeleteOne({'_id': document["_id"]}))

    if updates:
        await collection.bulk_write(updates)
        logger.info(f"Garbage collection purged {len(updates)} documents from the database")


async def listener(queue: asyncio.Queue, remove_garbage: bool = True):
    """
    Checks DB for new ReCaptcha jobs that are not in_queue and adds them to the shared queue for captcha_worker to solve
    """
    # Check for new requests inside the MongoDB Collection. If found, add to queue.
    # Immediately add 'in_queue' flag to prevent network errors from delaying 'captcha_id'
    db = MongoDB()
    collection = await db.get_collection()
    if remove_garbage:
        await purge_garbage(collection)
    garbage_collection_interval = int((GARBAGE_TIMER * 60) / HIT_DB_SLEEP)

    while True:
        try:
            for _ in range(garbage_collection_interval):
                updates = []
                query = {
                    "captcha_id": {"$exists": False},
                    "in_queue": {"$exists": False},
                }
                check = await collection.count_documents(query)
                if not check:
                    # logger.info("No job requests found, sleeping.")
                    await asyncio.sleep(HIT_DB_SLEEP)
                    continue
                results = collection.find(query)
                async for result in results:
                    updates.append(UpdateOne({'_id': result["_id"]}, {'$set': {'in_queue': True}}))
                    job = ReCaptchaInDb(**result)
                    await queue.put(job)
                in_queue = await collection.bulk_write(updates)
                await asyncio.sleep(HIT_DB_SLEEP)

            # Do garbage collection
            if remove_garbage:
                await purge_garbage(collection)

        except ServerSelectionTimeoutError as sste:
            logger.error(sste)
            await asyncio.sleep(HIT_DB_SLEEP * 2)
        except (TimeoutError, Exception) as e:
            logger.error(e)
            await asyncio.sleep(HIT_DB_SLEEP)


async def captcha_worker(queue: asyncio.Queue, worker_id: int):
    """
    Captcha workers get jobs from the queue and submit them to CapMonster via captcha_solver.py CaptchaUpload class
    """
    while True:
        captcha_request = await queue.get()
        success_flag = False
        attempts: int = int(os.getenv("SOLVE_ATTEMPTS")) or 3
        try:
            logger.info(f"Captcha Worker #{worker_id} received task from queue")
            db = MongoDB()
            collection = await db.get_collection()
            captcha = CaptchaUpload(collection, log=logging.getLogger(__name__))

            # Solve captcha
            possible_error_msg = ""
            for _ in range(attempts):
                try:
                    result = await captcha.solve_recaptcha(captcha_request)
                    success_flag = True
                    break
                except TimeoutError:
                    possible_error_msg = "TimeoutError"
                    continue
                except ReCaptchaError as rce:
                    if rce.text:
                        possible_error_msg = rce.text
                    if "ERROR_RECAPTCHA_TIMEOUT" in rce.text:
                        await asyncio.sleep(random.randint(5, 10))
                        continue
                    elif "banned" in rce.text.lower() or "error" in rce.text.lower():
                        await asyncio.sleep(10)
                        continue
                    else:
                        logger.error(rce)
                        # # Unhandled Errors, could exit immediately
                        # break
                except Exception as e:
                    possible_error_msg = str(e)

            if not success_flag:
                try:
                    u = await collection.update_one({"_id": ObjectId(captcha_request.id)},
                                                    {"$set":
                                                         {"error": str(possible_error_msg),
                                                          "in_queue": False,
                                                          "finished_on": datetime.datetime.now(tz=timezone.utc)}
                                                     })
                except Exception as e:
                    logger.error(f"MongoDB Exception thrown updating error message: {e}")
                    raise e
            queue.task_done()
            logger.info(f"{worker_id} finished task.")
        except Exception as e:
            logger.error(e)
            # Place unhandled Exceptions (failed jobs) back into queue indefinitely
            # (Bad idea to do this without a retry limit)
            logger.info("Placing request back in queue")
            await queue.put(captcha_request)


async def run_indefinitely():
    """
    Function to create captcha worker tasks that continuously wait for recaptcha jobs, solve, and update
    """
    queue = asyncio.Queue()

    listen_producer = [asyncio.create_task(listener(queue))]
    workers = [asyncio.create_task(captcha_worker(queue, _))
               for _ in range(SERVER_WORKERS)]
    logger.info(f"{SERVER_WORKERS} workers started")

    await asyncio.gather(*listen_producer)
    await queue.join()
    for w in workers:
        w.cancel()


asyncio.run(run_indefinitely())
