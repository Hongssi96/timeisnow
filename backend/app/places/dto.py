"""Request and response bodies for place endpoints."""
from uuid import UUID
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class SearchInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    query: str

    @field_validator('query')
    @classmethod
    def query_length(cls, value):
        value = value.strip()
        if not 1 <= len(value) <= 100:
            raise ValueError('Invalid query')
        return value


class Location(BaseModel):
    model_config = ConfigDict(extra='forbid')
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)


class PlaceInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    label: str
    location: Location
    source: Literal['search', 'map_pin'] = 'search'
    search_id: UUID | None = None
    candidate_id: UUID | None = None
    entrance_ref: None = None
    entrance_note: str | None = None
    location_confirmation_id: UUID | None = None

    @model_validator(mode='after')
    def creation_source(self):
        if self.source == 'search' and (self.search_id is None or self.candidate_id is None):
            raise ValueError('Search requires candidate')
        if self.source == 'map_pin' and (self.location_confirmation_id is None
                or self.search_id is not None or self.candidate_id is not None):
            raise ValueError('Pin requires confirmation without search candidate')
        return self

    @field_validator('entrance_note')
    @classmethod
    def note_length(cls, value):
        if value is None:
            return None
        value = value.strip()
        if not 1 <= len(value) <= 100:
            raise ValueError('Invalid entrance note')
        return value

    @field_validator('label')
    @classmethod
    def label_length(cls, value):
        value = value.strip()
        if not 1 <= len(value) <= 30:
            raise ValueError('Invalid label')
        return value


class ConfirmationInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    location: Location


class PlaceUpdateInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_version: int = Field(ge=1, strict=True)
    location: Location | None = None
    location_confirmation_id: UUID | None = None
    entrance_note: str | None = None
    label: str | None = None
    note_length = field_validator('entrance_note')(PlaceInput.note_length.__func__)

    @field_validator('label')
    @classmethod
    def label_length(cls, value):
        if value is None:
            raise ValueError('Invalid label')
        return PlaceInput.label_length(value)

    @model_validator(mode='after')
    def update_fields(self):
        if not {'label', 'location', 'entrance_note'} & self.model_fields_set:
            raise ValueError('No changes')
        if 'location' in self.model_fields_set and (self.location is None or self.location_confirmation_id is None):
            raise ValueError('Location requires confirmation')
        if self.location_confirmation_id is not None and self.location is None:
            raise ValueError('Confirmation requires location')
        return self
