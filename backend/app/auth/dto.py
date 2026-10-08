"""Request and response bodies for the auth endpoints."""
import re

from pydantic import BaseModel, ConfigDict, field_validator


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
