from fastapi_users import models


class User(models.BaseUser):
    pass


class UserCreate(models.BaseUserCreate):
    """
    Force disable is_superuser && is_verified for newly registered users
    """
    is_superuser = False
    is_verified = False


class UserUpdate(models.BaseUserUpdate):
    pass


class UserDB(User, models.BaseUserDB):
    pass
