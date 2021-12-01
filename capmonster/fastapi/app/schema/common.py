import uuid
from datetime import datetime, timezone
from typing import Optional
from enum import Enum
from bson import ObjectId
from pydantic import BaseModel, BaseConfig, validator, Field, Extra


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return str(ObjectId(v))

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")


class ConfigModel(BaseModel):
    def dict(self, by_alias=True, exclude_none=True, exclude_unset=True, **kwargs):
        return super().dict(
            by_alias=by_alias,
            exclude_none=exclude_none,
            **kwargs)

    def json(self, by_alias=True, exclude_none=True, **kwargs):
        return super().json(by_alias=by_alias, exclude_none=exclude_none, exclude_unset=True, **kwargs)

    class Config(BaseConfig):
        allow_population_by_alias = True
        allow_population_by_field_name = True
        json_encoders = {
            datetime: lambda dt: dt.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z"),
            ObjectId: str
        }


class DateTimeModelMixin(BaseModel):
    created_on: Optional[datetime]
    finished_on: Optional[datetime]

    @validator("created_on", pre=True, always=True)
    def default_datetime(cls, v: datetime) -> datetime:
        if not isinstance(v, datetime):
            return datetime.now(tz=timezone.utc)
        return v


class DBModelMixin(BaseModel):
    id: PyObjectId = Field(default_factory=uuid.uuid4, alias="_id")


class ProxyTypeEnum(str, Enum):
    http = "HTTP"
    https = "HTTPS"
    socks4 = "SOCKS4"
    socks5 = "SOCKS5"
