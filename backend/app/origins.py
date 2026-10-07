"""Validate a transient departure input without storing precise device locations."""
from datetime import datetime, timedelta, timezone
import re
from typing import Annotated, Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app import auth, places

router = APIRouter(prefix='/api/v1')


class CurrentOrigin(places.Location):
    type: Literal['current_location']
    accuracy_meters: float = Field(ge=0, allow_inf_nan=False)
    captured_at: datetime

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


class MapOrigin(places.Location):
    type: Literal['map_pin']


class SavedOrigin(BaseModel):
    model_config = ConfigDict(extra='forbid')
    type: Literal['saved_place']
    place_id: str
    location_version: int | None = Field(default=None, ge=1, strict=True)


class OriginInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    origin: Annotated[CurrentOrigin | MapOrigin | SavedOrigin, Field(discriminator='type')]


@router.post('/origin-validations')
def validate_origin(request: Request, body: OriginInput):
    with auth.database() as connection:
        user_id = places.authenticated(connection, request, True)
        _, secret, _ = auth.settings()
        auth.increment(connection, auth.bucket(connection, 'origin-validation', str(user_id), 60, 10, secret))
    with auth.database() as connection:
        places.authenticated(connection, request, True)
        if isinstance(body.origin, SavedOrigin):
            row = connection.execute('SELECT * FROM saved_places WHERE id=%s AND user_id=%s FOR SHARE',
                                     (places.parsed_id(body.origin.place_id), user_id)).fetchone()
            if not row:
                places.missing()
            if body.origin.location_version is not None and body.origin.location_version != row['location_version']:
                raise auth.AuthError(409, 'VERSION_CONFLICT', '장소 위치가 변경됐어요. 다시 선택해주세요.')
            return auth.answer(request, {'origin': {'type':'saved_place','place_id':str(row['id']),
                'location_version':row['location_version']}, 'label':row['label'],
                'location':{'latitude':row['latitude'],'longitude':row['longitude']},
                'location_address':row['location_address'] or row['address'],
                'quality_status':'not_applicable',
                'expires_at':auth.iso(datetime.now(timezone.utc)+timedelta(seconds=600))})
    location = places.Location(latitude=body.origin.latitude, longitude=body.origin.longitude)
    address = places.region_for_location(location)
    with auth.database() as connection:
        places.authenticated(connection, request, True)
    return auth.answer(request, {'origin':body.origin.model_dump(mode='json'),
        'label':'현재 위치' if isinstance(body.origin, CurrentOrigin) else '지도 선택 위치',
        'location':location.model_dump(), 'location_address':address,
        'quality_status':'pending' if isinstance(body.origin, CurrentOrigin) else 'not_applicable',
        'expires_at':auth.iso(datetime.now(timezone.utc)+timedelta(seconds=600))})
