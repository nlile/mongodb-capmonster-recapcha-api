import random
import string
from pydantic import BaseModel, validator

from app.schema.common import DateTimeModelMixin, DBModelMixin


class APIKeyCaptchaBase(BaseModel):
    user: str  # User.id


class APIKeyCaptcha(APIKeyCaptchaBase):
    user: str
    key: str
    credits: int


class APIKeyCaptchaCreate(APIKeyCaptchaBase, DateTimeModelMixin):
    key: str = None
    credits: int = 10

    @validator("key", pre=True, always=True)
    def generate_key(cls, v) -> str:
        if not isinstance(v, str):
            return ''.join(random.SystemRandom().choice(string.ascii_lowercase + string.digits) for _ in range(32))
        return v


class APIKeyInDb(APIKeyCaptcha, DBModelMixin):
    pass


class APIKeyUpdate(APIKeyCaptcha, DBModelMixin):
    pass


class APIKeyCaptchaInResponse(APIKeyCaptchaBase):
    key: str
    credits: int
