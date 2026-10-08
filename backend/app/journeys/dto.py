"""Request bodies for journey searches, reusing origin endpoint models."""
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.origins.dto import CurrentOrigin, MapOrigin, SavedOrigin


class CurrentLocation(CurrentOrigin):
    location_confirmed: bool = Field(strict=True)

    @field_validator('location_confirmed')
    @classmethod
    def confirmed(cls, value):
        if value is not True:
            raise ValueError('Manual confirmation required')
        return value


Endpoint = Annotated[CurrentLocation | MapOrigin | SavedOrigin, Field(discriminator='type')]


class Timing(BaseModel):
    model_config = ConfigDict(extra='forbid')
    mode: Literal['depart_now','arrive_by']
    timezone: Literal['Asia/Seoul']
    arrive_by: datetime | None = None


class Preferences(BaseModel):
    model_config = ConfigDict(extra='forbid')
    route_preference: Literal['balanced','fewer_transfers','less_walking']


class SearchInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    origin: Endpoint
    destination: Endpoint
    timing: Timing
    preferences: Preferences | None = None
