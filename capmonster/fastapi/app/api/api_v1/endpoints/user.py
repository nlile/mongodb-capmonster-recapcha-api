from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.users import jwt_authentication, fastapi_users, current_active_user
from app.core.config import settings
from app.crud.api_key import create_api_key, get_api_key
from app.db.mongodb import get_database
from app.schema.api_key import APIKeyCaptchaBase, APIKeyCaptchaInResponse
from app.schema.user import UserDB

router = APIRouter()


router.include_router(
    fastapi_users.get_auth_router(jwt_authentication), prefix="/auth/jwt", tags=["auth"],
)

if settings.REGISTRATION_ENABLED:
    router.include_router(
        fastapi_users.get_register_router(), prefix="/auth", tags=["auth"],
    )

router.include_router(
    fastapi_users.get_reset_password_router(),
    prefix="/auth",
    tags=["auth"],
)
router.include_router(
    fastapi_users.get_verify_router(),
    prefix="/auth",
    tags=["auth"],
)
router.include_router(fastapi_users.get_users_router(), prefix="/users",
                      tags=["users"])


@router.get("/users/generate-apikey", response_model=APIKeyCaptchaInResponse)
async def generate_apikey_route(db: AsyncIOMotorClient = Depends(get_database),
                                user: UserDB = Depends(current_active_user)):
    if not user.is_verified:
        raise HTTPException(
            status_code=401,
            detail=f"You are not verified. Please confirm your email.",
        )
    key_already_exists = await get_api_key(db, user_id=str(user.id))
    if key_already_exists:
        raise HTTPException(status_code=400, detail=f"User {user.id} already has an API Key.")
    new_api_key = APIKeyCaptchaBase(user=str(user.id))
    return await create_api_key(db, new_api_key)


