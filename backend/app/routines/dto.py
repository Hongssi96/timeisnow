"""Request bodies and rule validators for routine endpoints."""
import re
from datetime import time
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StringConstraints, StrictInt, model_validator

from app.common.errors import AuthError

# ISO-8601 weekday numbers: 1=Monday ... 7=Sunday, Asia/Seoul.
WEEKDAY_LIMITS = range(1, 8)
ARRIVAL_TIME = re.compile(r'([01]\d|2[0-3]):([0-5]\d)$')


def checked_weekdays(values):
    if not values or len(values) > 7 or len(set(values)) != len(values) \
            or any(value not in WEEKDAY_LIMITS for value in values):
        raise AuthError(422, 'VALIDATION_ERROR', '요일은 월(1)부터 일(7)까지 숫자로 중복 없이 1개 이상 보내주세요.')


def target_time_value(value):
    if value is None:
        return None
    match = ARRIVAL_TIME.fullmatch(value)
    if not match:
        raise AuthError(422, 'VALIDATION_ERROR', '목표 도착 시각은 HH:MM 형식으로 보내주세요.')
    return time(int(match.group(1)), int(match.group(2)))


class RoutineInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=30)]
    origin_place_id: UUID
    destination_place_id: UUID
    search_id: UUID
    candidate_id: UUID
    weekdays: list[StrictInt]
    target_arrival_local_time: str | None = None

    @model_validator(mode='after')
    def distinct_places(self):
        if self.origin_place_id == self.destination_place_id:
            raise ValueError('Same origin and destination place')
        return self

    @model_validator(mode='after')
    def repeat_weekdays(self):
        checked_weekdays(self.weekdays)
        return self

    @model_validator(mode='after')
    def valid_target(self):
        target_time_value(self.target_arrival_local_time)
        return self


class RoutineScheduleInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_version: StrictInt
    name: Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=30)] | None = None
    origin_place_id: UUID | None = None
    destination_place_id: UUID | None = None
    search_id: UUID | None = None
    candidate_id: UUID | None = None
    weekdays: list[StrictInt] | None = None
    target_arrival_local_time: str | None = None

    @model_validator(mode='after')
    def repeat_weekdays(self):
        if self.weekdays is not None:
            checked_weekdays(self.weekdays)
        return self

    @model_validator(mode='after')
    def valid_target(self):
        target_time_value(self.target_arrival_local_time)
        return self

    @model_validator(mode='after')
    def complete_changes(self):
        for field in ('name', 'weekdays'):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError('Name and weekdays cannot be null')
        route_fields = {'origin_place_id', 'destination_place_id', 'search_id', 'candidate_id'}
        supplied = route_fields & self.model_fields_set
        if supplied and (supplied != route_fields or any(getattr(self, field) is None for field in route_fields)):
            raise ValueError('All route references are required together')
        if supplied and self.origin_place_id == self.destination_place_id:
            raise ValueError('Same origin and destination place')
        return self

    @model_validator(mode='after')
    def positive_version(self):
        if self.expected_version < 1:
            raise ValueError('Expected version must be positive')
        return self
