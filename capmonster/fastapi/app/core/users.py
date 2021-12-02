from fastapi_users import FastAPIUsers
from fastapi_users.authentication import JWTAuthentication

from app.core.config import settings
from app.schema.user import UserDB, User, UserCreate, UserUpdate
from app.core.user_manager import get_user_manager

ACCESS_TOKEN_EXPIRE_SECONDS = (int(settings.ACCESS_TOKEN_EXPIRE_MINUTES) * 60)

jwt_authentication = JWTAuthentication(
    secret=settings.FASTAPI_USERS_SECRET_KEY, lifetime_seconds=ACCESS_TOKEN_EXPIRE_SECONDS,
    tokenUrl=settings.API_V1_STR + "/auth/jwt/login "
)

fastapi_users = FastAPIUsers(
    get_user_manager,
    [jwt_authentication],
    User,
    UserCreate,
    UserUpdate,
    UserDB,
)

current_active_user = fastapi_users.current_user(active=True)