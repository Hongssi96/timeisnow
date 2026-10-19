"""Request and response bodies for the auth endpoints."""
import re

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class LoginInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    email: str
    password: str

    @field_validator('email')
    @classmethod
    def email_format(cls, value):
        value = value.strip().lower()
        if len(value) > 254 or not re.fullmatch(r"[a-z0-9!#$%&'*+/=?^_`{|}~.-]+@[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?\.[a-z]{2,63}", value):
            raise ValueError('Invalid email')
        local, domain = value.rsplit('@', 1)
        if len(local) > 64 or local.startswith('.') or local.endswith('.') or '..' in value or any(not label or len(label)>63 or label.startswith('-') or label.endswith('-') for label in domain.split('.')):
            raise ValueError('Invalid email')
        return value

    @field_validator('password')
    @classmethod
    def password_length(cls, value):
        if not 15 <= len(value) <= 128:
            raise ValueError('Invalid password')
        return value


class RegisterInput(LoginInput):
    display_name: str

    @field_validator('display_name')
    @classmethod
    def name_length(cls, value):
        value = value.strip()
        if not 1 <= len(value) <= 30:
            raise ValueError('Invalid name')
        return value

    @field_validator('password')
    @classmethod
    def weak_password(cls, value):
        if value.lower() in {'123456789012345', '1234567890123456', 'passwordpassword', 'qwertyuiopasdfgh', 'aaaaaaaaaaaaaaa'}:
            raise ValueError('Weak password')
        return value


class EmptyInput(BaseModel):
    model_config = ConfigDict(extra='forbid')


class ProfileInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_version: int = Field(strict=True, ge=1)
    walking_preference: Literal['slow','normal','fast'] | None = None
    first_boarding_buffer_seconds: int | None = Field(default=None, strict=True, ge=0, le=1800)
    transfer_buffer_seconds: int | None = Field(default=None, strict=True, ge=0, le=1800)
    route_preference: Literal['balanced','fewer_transfers','less_walking'] | None = None

    @model_validator(mode='after')
    def changes(self):
        fields=self.model_fields_set-{'expected_version'}
        if not fields or any(getattr(self,key) is None for key in fields):
            raise ValueError('At least one non-null setting is required')
        return self
