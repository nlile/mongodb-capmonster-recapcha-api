from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, BaseConfig, validator, Field, Extra, HttpUrl

from ..schema.common import ConfigModel, DateTimeModelMixin, DBModelMixin, ProxyTypeEnum


class CaptchaBase(ConfigModel):
    # api_key: str = Field(..., alias="key")
    pageurl: HttpUrl
    proxy: Optional[str]
    proxytype: Optional[ProxyTypeEnum]

    @validator("proxy", pre=True, always=True)
    def incorrect_proxy_format(cls, v: str):
        """
        Strips http:// from the proxy string if present. Robust implementation would update proxytype if mismatched
        """
        if not v:
            return None
        if "://" in v:
            return v.split('://')[1]
        return v


class ReCaptcha(CaptchaBase):
    method: str = "userrecaptcha"
    googlekey: str


class ReCaptchaCreate(ReCaptcha):
    api_key: str = Field(..., alias="key")

    class Config:
        schema_extra = {
            "example": {
                "api_key": "1abc234de56fab7c89012d34e56fa7b8",
                "googlekey": "6Le-wvkSAAAAAPBMRTvw0Q4Muexq9bi0DJwx_mJ-",
                "pageurl": "https://www.google.com/recaptcha/api2/demo",
                "proxy": "username:password@192.168.0.1:1500",
                "proxytype": "HTTP",
            }
        }


class ReCaptchaInCreate(ReCaptchaCreate, DateTimeModelMixin):
    # Adds created_on
    pass


class ReCaptchaInDb(ReCaptcha, DBModelMixin):
    # Inserts ID
    pass


class ReCaptchaResponse(ReCaptcha, DateTimeModelMixin):
    action: str = "get"
    captcha_id: Optional[int]
    status: Optional[str]
    # Either remove status or change error to status
    error: Optional[str]
    in_queue: Optional[bool]


class ReCaptchaErrorResponse(ReCaptchaResponse, extra=Extra.allow):
    error: str


class ReCaptchaSolved(ReCaptchaResponse, extra=Extra.allow):
    solution: str
    finished_on = datetime.now()
    in_queue = False


class ReCaptchaResponse2Captcha(BaseModel):
    response: str = "CAPCHA_NOT_READY"
