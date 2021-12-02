from fastapi import FastAPI
from starlette.middleware.gzip import GZipMiddleware
from starlette.requests import Request
from starlette.responses import Response
from fastapi.responses import PlainTextResponse
from app.core.config import settings
from app.api.api_v1.api import router as endpoint_router
from app.db.mongodb import close, connect

app = FastAPI(title=settings.PROJECT_NAME,
              description=settings.APP_DESCRIPTION,
              version=settings.PROJECT_VERSION)

app.add_middleware(GZipMiddleware, minimum_size=1000)

app.include_router(endpoint_router, prefix=settings.API_V1_STR)


@app.on_event("startup")
async def on_app_start():
    """
    Anything that needs to happen while the app starts
    """
    await connect()


@app.on_event("shutdown")
async def on_app_shutdown():
    """
    Anything that needs to happen while the app shuts down
    """
    await close()


@app.get("/", response_class=PlainTextResponse)
async def home():
    """
    The home page
    """
    return PlainTextResponse('{"online": True}', status_code=200)
