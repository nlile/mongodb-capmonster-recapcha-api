from typing import Optional
from fastapi import Depends, Request
from fastapi_users import BaseUserManager

from app.core.config import settings
from app.db.users_db import get_user_db
from app.schema.user import UserCreate, UserDB


class UserManager(BaseUserManager[UserCreate, UserDB]):
    user_db_model = UserDB
    reset_password_token_secret = settings.FASTAPI_USERS_SECRET_KEY
    verification_token_secret = settings.FASTAPI_USERS_SECRET_KEY

    async def on_after_register(self, user: UserDB, request: Optional[Request] = None):
        print(f"User {user.id} has registered.")

    async def on_after_forgot_password(
        self, user: UserDB, token: str, request: Optional[Request] = None
    ):
        print(f"User {user.id} has forgot their password. Reset token: {token}")

    async def on_after_request_verify(
        self, user: UserDB, token: str, request: Optional[Request] = None
    ):
        print(f"Verification requested for user {user.id}. Verification token: {token}")


def get_user_manager(user_db=Depends(get_user_db)):
    yield UserManager(user_db)
