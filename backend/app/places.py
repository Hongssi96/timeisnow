"""Place search and storage. Never log queries, coordinates or provider payloads."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from uuid import UUID, uuid4

from fastapi import APIRouter, Query, Request
from fastapi.responses import Response
from psycopg.types.json import Jsonb
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from dotenv import dotenv_values

from app import auth

router = APIRouter(prefix='/api/v1')


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def provider_search(kind, query, key):
    url = 'https://dapi.kakao.com/v2/local/search/' + kind + '.json?'
    return provider_documents(url, {'query': query, 'size': 10}, key)


def provider_documents(url, params, key):
    request = urllib.request.Request(url + urllib.parse.urlencode(params),
                                     headers={'Authorization': 'KakaoAK ' + key})
    try:
        with urllib.request.build_opener(NoRedirect).open(request, timeout=3) as response:
            # Bound provider data even when the upstream response is unexpected.
            raw = response.read(262145)
            if len(raw) > 262144:
                raise ValueError()
            data = json.loads(raw)
            if not isinstance(data, dict) or not isinstance(data.get('documents'), list):
                raise ValueError()
            return data['documents']
    except (ValueError, TypeError, UnicodeError):
        raise auth.AuthError(502, 'PROVIDER_RESPONSE_INVALID', '검색 결과를 확인할 수 없어요.') from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise auth.AuthError(503, 'PROVIDER_UNAVAILABLE', '장소 검색에 연결할 수 없어요.') from None


def region_for_location(location):
    values = {**dotenv_values(auth.ROOT / '.env'), **os.environ}
    key = values.get('KAKAO_REST_API_KEY')
    if not key:
        raise auth.AuthError(503, 'PROVIDER_UNAVAILABLE', '선택한 위치를 확인할 수 없어요.')
    documents = provider_documents('https://dapi.kakao.com/v2/local/geo/coord2regioncode.json?',
        {'x': location.longitude, 'y': location.latitude, 'input_coord': 'WGS84'}, key)
    try:
        for document in documents:
            if not isinstance(document, dict) or document.get('region_type') not in ('B', 'H'):
                raise ValueError()
            if document['region_type'] != 'B':
                continue
            region, address = document['region_1depth_name'], document['address_name']
            if not isinstance(region, str) or not isinstance(address, str) or not address:
                raise ValueError()
            if region in ('서울', '서울특별시', '경기', '경기도'):
                return address
    except (ValueError, KeyError, TypeError):
        raise auth.AuthError(502, 'PROVIDER_RESPONSE_INVALID', '선택한 위치를 확인할 수 없어요.') from None
    raise auth.AuthError(422, 'UNSUPPORTED_REGION', '서울·경기 안에서 위치를 선택해주세요.')


def search_candidates(query):
    values = {**dotenv_values(auth.ROOT / '.env'), **os.environ}
    key = values.get('KAKAO_REST_API_KEY')
    if not key:
        raise auth.AuthError(503, 'PROVIDER_UNAVAILABLE', '장소 검색에 연결할 수 없어요.')
    candidates, seen = [], set()
    for kind in ('address', 'keyword'):
        for doc in provider_search(kind, query, key):
            try:
                address = doc['address_name']
                lat, lon = float(doc['y']), float(doc['x'])
                if (not isinstance(address, str) or not address or not math.isfinite(lat)
                        or not math.isfinite(lon) or not -90 <= lat <= 90 or not -180 <= lon <= 180):
                    raise ValueError()
                # Administrative address from the provider, not a guessed bounding box.
                if address.split()[0] not in ('서울', '서울특별시', '경기', '경기도'):
                    continue
                road = doc.get('road_address') or {}
                name = doc.get('place_name') or road.get('building_name') or address
                if not isinstance(name, str) or not name:
                    raise ValueError()
                identity = (address, lat, lon)
                if identity in seen:
                    continue
                seen.add(identity)
                candidates.append({'candidate_id': str(uuid4()), 'name': name, 'address': address,
                                   'location': {'latitude': lat, 'longitude': lon}})
            except (ValueError, TypeError, KeyError, AttributeError, IndexError):
                raise auth.AuthError(502, 'PROVIDER_RESPONSE_INVALID', '검색 결과를 확인할 수 없어요.') from None
    return candidates[:20]


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
    search_id: UUID
    candidate_id: UUID
    entrance_ref: None = None
    entrance_note: str | None = None
    location_confirmation_id: UUID | None = None

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


def authenticated(connection, request, write=False):
    origin, _, secure = auth.settings()
    row = auth.session(connection, request, secure, required=True)
    if write:
        auth.require_csrf(connection, request, origin, secure)
    connection.execute("UPDATE auth_sessions SET idle_expires_at=LEAST(absolute_expires_at,now()+interval '24 hours') WHERE token_hash=%s", (row['token_hash'],))
    return row['user_id']


def missing():
    raise auth.AuthError(404, 'RESOURCE_NOT_FOUND', '장소 또는 검색 결과를 찾을 수 없어요. 다시 검색해주세요.')


def parsed_id(value):
    try:
        return UUID(value)
    except (ValueError, TypeError):
        missing()


def place_data(row):
    return {'place_id': str(row['id']), 'label': row['label'], 'name': row['name'],
            'address': row['address'], 'location': {'latitude': row['latitude'], 'longitude': row['longitude']},
            'entrance_ref': row['entrance_ref'], 'version': row['version'],
            'entrance_note': row['entrance_note'], 'location_source': row['location_source'],
            'location_address': row['location_address'], 'location_version': row['location_version']}


def confirmed_location(connection, user_id, confirmation_id, location):
    row = connection.execute('''SELECT * FROM place_location_confirmations
        WHERE id=%s AND user_id=%s AND expires_at > now()''', (confirmation_id, user_id)).fetchone()
    if not row:
        missing()
    if (row['latitude'], row['longitude']) != (location.latitude, location.longitude):
        raise auth.AuthError(422, 'VALIDATION_ERROR', '핀 위치를 다시 확인해주세요.')
    return row['location_address']


@router.get('/map-config')
def map_config(request: Request):
    with auth.database() as connection:
        authenticated(connection, request)
    values = {**dotenv_values(auth.ROOT / '.env'), **os.environ}
    key = values.get('KAKAO_JAVASCRIPT_KEY')
    if not key:
        raise auth.AuthError(503, 'MAP_UNAVAILABLE', '지도를 불러올 수 없어요.')
    # This is the public, domain-restricted SDK key; never expose the REST key.
    return auth.answer(request, {'javascript_key': key})


@router.post('/place-location-confirmations')
def confirm(request: Request, body: ConfirmationInput):
    with auth.database() as connection:
        user_id = authenticated(connection, request, True)
        _, secret, _ = auth.settings()
        auth.increment(connection, auth.bucket(connection, 'place-location', str(user_id), 60, 10, secret))
        connection.execute('DELETE FROM place_location_confirmations WHERE expires_at <= now()')
    address = region_for_location(body.location)
    confirmation_id, expires = uuid4(), datetime.now(timezone.utc) + timedelta(seconds=600)
    with auth.database() as connection:
        user_id = authenticated(connection, request, True)
        connection.execute('INSERT INTO place_location_confirmations VALUES(%s,%s,%s,%s,%s,%s)',
            (confirmation_id, user_id, body.location.latitude, body.location.longitude, address, expires))
    return auth.answer(request, {'confirmation_id': str(confirmation_id), 'location': body.location.model_dump(),
                                'location_address': address, 'expires_at': auth.iso(expires)})


@router.post('/place-searches')
def search(request: Request, body: SearchInput):
    # Commit the quota before contacting the provider; upstream failures still count.
    with auth.database() as connection:
        user_id = authenticated(connection, request, True)
        _, secret, _ = auth.settings()
        auth.increment(connection, auth.bucket(connection, 'place-search', str(user_id), 60, 10, secret))
        connection.execute('DELETE FROM place_searches WHERE expires_at <= now()')
    candidates = search_candidates(body.query)
    search_id = uuid4()
    expires = datetime.now(timezone.utc) + timedelta(seconds=600)
    with auth.database() as connection:
        # Session could have been revoked while the upstream call was running.
        user_id = authenticated(connection, request, True)
        connection.execute('INSERT INTO place_searches VALUES(%s,%s,%s,%s)',
                           (search_id, user_id, Jsonb(candidates), expires))
    return auth.answer(request, {'search_id': str(search_id), 'expires_at': auth.iso(expires), 'candidates': candidates})


@router.post('/places')
def create(request: Request, body: PlaceInput):
    key = request.headers.get('idempotency-key')
    if key is not None and not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', key):
        raise auth.AuthError(422, 'VALIDATION_ERROR', '입력값을 확인해주세요.')
    canonical = body.model_dump(mode='json')
    # Preserve F03-01 retry hashes when the new optional fields are omitted/null.
    for field in ('entrance_note', 'location_confirmation_id'):
        if canonical[field] is None:
            canonical.pop(field)
    fingerprint = hashlib.sha256(json.dumps(canonical, sort_keys=True).encode()).hexdigest()
    with auth.database() as connection:
        user_id = authenticated(connection, request, True)
        connection.execute('DELETE FROM place_creation_keys WHERE expires_at <= now()')
        if key:
            # Per-user session lock above serializes same-session writes; advisory lock also covers other sessions.
            connection.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))', (str(user_id) + ':' + key,))
            previous = connection.execute('SELECT * FROM place_creation_keys WHERE user_id=%s AND key=%s', (user_id, key)).fetchone()
            if previous:
                if previous['body_hash'] != fingerprint:
                    raise auth.AuthError(409, 'IDEMPOTENCY_CONFLICT', '다른 저장 요청이에요. 다시 확인해주세요.')
                row = connection.execute('SELECT * FROM saved_places WHERE id=%s AND user_id=%s', (previous['place_id'], user_id)).fetchone()
                if not row:
                    missing()
                return auth.answer(request, place_data(row), 201)
        result = connection.execute('SELECT candidates FROM place_searches WHERE id=%s AND user_id=%s AND expires_at > now()',
                                    (body.search_id, user_id)).fetchone()
        candidate = next((item for item in result['candidates'] if item['candidate_id'] == str(body.candidate_id)), None) if result else None
        if not candidate:
            missing()
        location_address = None
        if body.location_confirmation_id:
            location_address = confirmed_location(connection, user_id, body.location_confirmation_id, body.location)
        elif candidate['location'] != body.location.model_dump():
            raise auth.AuthError(422, 'VALIDATION_ERROR', '선택한 장소를 다시 확인해주세요.')
        row = connection.execute('''INSERT INTO saved_places(id,user_id,label,name,address,latitude,longitude,entrance_note,location_source,location_address)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *''',
            (uuid4(), user_id, body.label, candidate['name'], candidate['address'], body.location.latitude,
             body.location.longitude, body.entrance_note, 'map_pin' if body.location_confirmation_id else 'search', location_address)).fetchone()
        if key:
            connection.execute("INSERT INTO place_creation_keys VALUES(%s,%s,%s,%s,now()+interval '24 hours')", (user_id, key, fingerprint, row['id']))
    return auth.answer(request, place_data(row), 201)


@router.patch('/places/{place_id}')
def update(request: Request, place_id: str, body: PlaceUpdateInput):
    with auth.database() as connection:
        user_id = authenticated(connection, request, True)
        row = connection.execute('SELECT * FROM saved_places WHERE id=%s AND user_id=%s FOR UPDATE',
                                 (parsed_id(place_id), user_id)).fetchone()
        if not row:
            missing()
        if row['version'] != body.expected_version:
            raise auth.AuthError(409, 'VERSION_CONFLICT', '장소가 변경됐어요. 최신 위치를 다시 확인해주세요.')
        latitude, longitude = row['latitude'], row['longitude']
        source, address = row['location_source'], row['location_address']
        if body.location:
            address = confirmed_location(connection, user_id, body.location_confirmation_id, body.location)
            latitude, longitude = body.location.latitude, body.location.longitude
            source = 'map_pin'
        note = body.entrance_note if 'entrance_note' in body.model_fields_set else row['entrance_note']
        label = body.label if 'label' in body.model_fields_set else row['label']
        location_changed = (latitude, longitude, source, note) != (row['latitude'], row['longitude'], row['location_source'], row['entrance_note'])
        if location_changed or label != row['label']:
            row = connection.execute('''UPDATE saved_places SET latitude=%s,longitude=%s,location_source=%s,
                location_address=%s,entrance_note=%s,label=%s,version=version+1,
                location_version=location_version+%s,updated_at=now()
                WHERE id=%s AND user_id=%s RETURNING *''', (latitude, longitude, source, address, note, label,
                int(location_changed), row['id'], user_id)).fetchone()
    return auth.answer(request, place_data(row))


@router.delete('/places/{place_id}')
def delete(request: Request, place_id: str):
    with auth.database() as connection:
        user_id = authenticated(connection, request, True)
        row = connection.execute('SELECT id FROM saved_places WHERE id=%s AND user_id=%s FOR UPDATE',
                                 (parsed_id(place_id), user_id)).fetchone()
        if not row:
            missing()
        # FK SET NULL retains only the bounded retry marker, preventing late creation retries.
        connection.execute('DELETE FROM saved_places WHERE id=%s AND user_id=%s', (row['id'], user_id))
    return Response(status_code=204, headers={'Cache-Control': 'no-store'})


@router.get('/places')
def listing(request: Request, limit: int = Query(default=20, ge=1, le=100), cursor: str | None = None):
    with auth.database() as connection:
        user_id = authenticated(connection, request)
        cursor_id = parsed_id(cursor) if cursor is not None else None
        if cursor_id and not connection.execute('SELECT id FROM saved_places WHERE id=%s AND user_id=%s', (cursor_id, user_id)).fetchone():
            missing()
        rows = connection.execute('SELECT * FROM saved_places WHERE user_id=%s AND (%s::uuid IS NULL OR id < %s::uuid) ORDER BY id DESC LIMIT %s',
                                  (user_id, cursor_id, cursor_id, limit + 1)).fetchall()
    return auth.answer(request, {'items': [place_data(row) for row in rows[:limit]],
                                'next_cursor': str(rows[limit-1]['id']) if len(rows) > limit else None})


@router.get('/places/{place_id}')
def detail(request: Request, place_id: str):
    with auth.database() as connection:
        user_id = authenticated(connection, request)
        row = connection.execute('SELECT * FROM saved_places WHERE id=%s AND user_id=%s', (parsed_id(place_id), user_id)).fetchone()
        if not row:
            missing()
    return auth.answer(request, place_data(row))
