"""Request bodies for departure origin validation."""
import re
from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.places.dto import Location


class CurrentOrigin(Location):
    type: Literal['current_location']
    accuracy_meters: float = Field(ge=0, allow_inf_nan=False)
    captured_at: datetime
    location_confirmed: bool = Field(default=False, strict=True)

    @field_validator('captured_at', mode='before')
    @classmethod
    def timestamp_string(cls, value):
        if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})', value):
            raise ValueError('Expected ISO timestamp')
        return value

    @field_validator('captured_at')
    @classmethod
    def timestamp_zone(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError('Timezone required')
        return value.astimezone(timezone.utc)


class MapOrigin(Location):
    type: Literal['map_pin']


class SavedOrigin(BaseModel):
    model_config = ConfigDict(extra='forbid')
    type: Literal['saved_place']
    place_id: str
    location_version: int | None = Field(default=None, ge=1, strict=True)


class OriginInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    origin: Annotated[CurrentOrigin | MapOrigin | SavedOrigin, Field(discriminator='type')]
