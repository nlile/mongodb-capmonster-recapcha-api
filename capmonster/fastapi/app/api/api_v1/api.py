from fastapi import APIRouter, Depends
from app.api.api_v1.endpoints.recaptcha import router as recaptcha_router
from app.api.api_v1.endpoints.user import router as user_router


router = APIRouter()
router.include_router(recaptcha_router)
router.include_router(user_router)

