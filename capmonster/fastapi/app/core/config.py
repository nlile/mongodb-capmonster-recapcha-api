from distutils.util import strtobool
from typing import Optional, Union, Dict, Any
import os
from pydantic import BaseSettings, Field, validator, PostgresDsn, EmailStr
from starlette.datastructures import CommaSeparatedStrings, Secret


class Settings(BaseSettings):
    PROJECT_NAME: str = os.getenv("PROJECT_NAME")
    PROJECT_VERSION: str = "0.0.1"
    API_V1_STR: str = os.getenv("API_V1_STR", "/api/v1")

    APP_DESCRIPTION: str = os.getenv("APP_DESCRIPTION")
    WEBSITE_URL: str = os.getenv("WEBSITE_URL", "http://localhost:5000")
    DOMAIN: str = os.getenv("DOMAIN")

    MDB_URI = os.getenv("MDB_URI")
    MDB_DATABASE = os.getenv("MDB_DATABASE")
    MDB_COLLECTION = os.getenv("MDB_COLLECTION")
    MDB_COLLECTION_USERS = os.getenv("MDB_COLLECTION_USERS", "users")
    MDB_COLLECTION_KEYS = os.getenv("MDB_COLLECTION_KEYS", "keys")

    MAX_CONNECTIONS_COUNT = int(os.getenv("MAX_CONNECTIONS_COUNT", 10))
    MIN_CONNECTIONS_COUNT = int(os.getenv("MIN_CONNECTIONS_COUNT", 10))
    # PAGINATION_LIMIT: int = int(os.getenv("PAGINATION_LIMIT"), 10)

    REGISTRATION_ENABLED: bool = strtobool(os.getenv("REGISTRATION_ENABLED", False))

    ALLOWED_HOSTS = CommaSeparatedStrings(os.getenv("ALLOWED_HOSTS", ""))

    SECRET_KEY: str = os.getenv("SECRET_KEY")
    FASTAPI_USERS_SECRET_KEY: str = os.getenv("FASTAPI_USERS_SECRET_KEY")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 180))
    ROOT_API_KEY = os.getenv("ROOT_API_KEY", "XXXXXXX")

    # Number of server.py solver workers to spawn
    SERVER_WORKERS = int(os.getenv("SERVER_WORKERS", 3))

    # Max number of retry attempts IF the captcha fails to solve
    SOLVE_ATTEMPTS = int(os.getenv("SOLVE_ATTEMPTS", 3))

    # Seconds before a captcha_solver.py httpx request throws a timeout
    HTTPX_TIMEOUT = int(os.getenv("HTTPX_TIMEOUT", 180))

    # Number of minutes before captcha database entries are removed
    GARBAGE_TIMER = int(os.getenv("GARBAGE_TIMER", 60))

    class Config:
        case_sensitive = True


settings = Settings()
