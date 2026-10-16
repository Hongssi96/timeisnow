"""Request bodies and rule validators for meeting core endpoints."""
import re
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, StrictInt, model_validator

from app.common.errors import AuthError
from app.journeys.dto import Endpoint

SUPPORTED_TIMEZONE = 'Asia/Seoul'
TOKEN_FORMAT = re.compile(r'[A-Za-z0-9_-]{32,256}$')


class DestinationInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=100)]
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)
    # F12 core stores a shared destination only; provider references stay out of scope.
    provider: None = None
    place_ref: None = None


class MeetingCreateInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    title: Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=100)]


class MeetingUpdateInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_version: StrictInt
    title: Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=100)]

    @model_validator(mode='after')
    def positive_version(self):
        if self.expected_version < 1:
            raise ValueError('Expected version must be positive')
        return self


class ConfirmationInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_version: StrictInt
    target_arrival_at: datetime
    timezone: str
    destination: DestinationInput

    @model_validator(mode='after')
    def rules(self):
        if self.expected_version < 1:
            raise ValueError('Expected version must be positive')
        # The service supports Asia/Seoul schedules only, like routines.
        if self.timezone != SUPPORTED_TIMEZONE:
            raise AuthError(422, 'VALIDATION_ERROR', '약속 시간대는 Asia/Seoul로 보내주세요.')
        if self.target_arrival_at.tzinfo is None or self.target_arrival_at.utcoffset() is None:
            raise AuthError(422, 'VALIDATION_ERROR', '목표 도착 시각은 시간대가 있는 ISO8601 형식으로 보내주세요.')
        return self


class TransitionInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_version: StrictInt
    status: Literal['completed', 'cancelled']

    @model_validator(mode='after')
    def positive_version(self):
        if self.expected_version < 1:
            raise ValueError('Expected version must be positive')
        return self


class InviteIssueInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_version: StrictInt

    @model_validator(mode='after')
    def positive_version(self):
        if self.expected_version < 1:
            raise ValueError('Expected version must be positive')
        return self


class InviteTokenInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    token: Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=32, max_length=256)]

    @model_validator(mode='after')
    def token_shape(self):
        if not TOKEN_FORMAT.fullmatch(self.token):
            raise AuthError(422, 'VALIDATION_ERROR', '초대 토큰 형식을 확인해주세요.')
        return self


class MemberOriginInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    origin: Endpoint
    recommendation_consent: bool
    expected_version: StrictInt

    @model_validator(mode='after')
    def positive_version(self):
        if self.expected_version < 1:
            raise ValueError('Expected version must be positive')
        return self


class GuidanceQueryInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    meeting_revision_id: str
    departure_basis: Literal['recommended', 'now']
    origin_override: Endpoint | None = None
    trip_id: str | None = None


def checked_idempotency_key(request):
    key = request.headers.get('idempotency-key')
    if key is None or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', key):
        raise AuthError(422, 'VALIDATION_ERROR', '요청 키(Idempotency-Key)를 1~128자로 보내주세요.')
    return key


def meeting_id_value(value):
    try:
        return UUID(value)
    except (ValueError, TypeError):
        raise AuthError(404, 'RESOURCE_NOT_FOUND', '약속을 찾을 수 없어요. 이미 삭제됐거나 참여하지 않은 약속이에요.') from None
