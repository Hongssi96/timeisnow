"""Place business rules: pin confirmation, idempotent storage and version conflicts."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import re
from uuid import UUID, uuid4

from psycopg.types.json import Jsonb

from app.auth import security
from app.common.database import database
from app.common.errors import AuthError
from app.common.timeutil import iso
from app.places import provider, repository


def missing():
    raise AuthError(404, 'RESOURCE_NOT_FOUND', '장소 또는 검색 결과를 찾을 수 없어요. 다시 검색해주세요.')


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
    row = repository.find_confirmation(connection, user_id, confirmation_id)
    if not row:
        missing()
    if (row['latitude'], row['longitude']) != (location.latitude, location.longitude):
        raise AuthError(422, 'VALIDATION_ERROR', '핀 위치를 다시 확인해주세요.')
    return row['location_address']


def map_config(request):
    with database() as connection:
        security.authenticated(connection, request)
    key = provider.javascript_key()
    if not key:
        raise AuthError(503, 'MAP_UNAVAILABLE', '지도를 불러올 수 없어요.')
    # This is the public, domain-restricted SDK key; never expose the REST key.
    return {'javascript_key': key}


def confirm(request, body):
    with database() as connection:
        user_id = security.authenticated(connection, request, True)
        _, secret, _ = security.settings()
        security.increment(connection, security.bucket(connection, 'place-location', str(user_id), 60, 10, secret))
        repository.delete_expired_confirmations(connection)
    address = provider.region_for_location(body.location)
    confirmation_id, expires = uuid4(), datetime.now(timezone.utc) + timedelta(seconds=600)
    with database() as connection:
        user_id = security.authenticated(connection, request, True)
        repository.insert_confirmation(connection, confirmation_id, user_id,
                                       body.location.latitude, body.location.longitude, address, expires)
    return {'confirmation_id': str(confirmation_id), 'location': body.location.model_dump(),
            'location_address': address, 'expires_at': iso(expires)}


def search(request, body):
    # Commit the quota before contacting the provider; upstream failures still count.
    with database() as connection:
        user_id = security.authenticated(connection, request, True)
        _, secret, _ = security.settings()
        security.increment(connection, security.bucket(connection, 'place-search', str(user_id), 60, 10, secret))
        repository.delete_expired_searches(connection)
    candidates = provider.search_candidates(body.query)
    search_id = uuid4()
    expires = datetime.now(timezone.utc) + timedelta(seconds=600)
    with database() as connection:
        # Session could have been revoked while the upstream call was running.
        user_id = security.authenticated(connection, request, True)
        repository.insert_search(connection, search_id, user_id, Jsonb(candidates), expires)
    return {'search_id': str(search_id), 'expires_at': iso(expires), 'candidates': candidates}


def create(request, body):
    key = request.headers.get('idempotency-key')
    if key is not None and not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', key):
        raise AuthError(422, 'VALIDATION_ERROR', '입력값을 확인해주세요.')
    canonical = body.model_dump(mode='json')
    if body.source == 'search':
        canonical.pop('source')
    # Preserve F03-01 retry hashes when the new optional fields are omitted/null.
    for field in ('entrance_note', 'location_confirmation_id'):
        if canonical[field] is None:
            canonical.pop(field)
    fingerprint = hashlib.sha256(json.dumps(canonical, sort_keys=True).encode()).hexdigest()
    with database() as connection:
        user_id = security.authenticated(connection, request, True)
        repository.delete_expired_creation_keys(connection)
        if key:
            # Per-user session lock above serializes same-session writes; advisory lock also covers other sessions.
            repository.advisory_lock(connection, str(user_id) + ':' + key)
            previous = repository.find_creation_key(connection, user_id, key)
            if previous:
                if previous['body_hash'] != fingerprint:
                    raise AuthError(409, 'IDEMPOTENCY_CONFLICT', '다른 저장 요청이에요. 다시 확인해주세요.')
                row = repository.find_place(connection, previous['place_id'], user_id)
                if not row:
                    missing()
                return place_data(row)
        location_address = None
        if body.source == 'map_pin':
            location_address = confirmed_location(connection, user_id, body.location_confirmation_id, body.location)
            name, address = body.label, location_address
        else:
            result = repository.find_search(connection, body.search_id, user_id)
            candidate = next((item for item in result['candidates'] if item['candidate_id'] == str(body.candidate_id)), None) if result else None
            if not candidate: missing()
            name, address = candidate['name'], candidate['address']
            if body.location_confirmation_id:
                location_address = confirmed_location(connection, user_id, body.location_confirmation_id, body.location)
            elif candidate['location'] != body.location.model_dump():
                raise AuthError(422, 'VALIDATION_ERROR', '선택한 장소를 다시 확인해주세요.')
        row = repository.insert_place(connection, (uuid4(), user_id, body.label, name, address,
                                                   body.location.latitude, body.location.longitude, body.entrance_note,
                                                   'map_pin' if body.location_confirmation_id else 'search', location_address))
        if key:
            repository.insert_creation_key(connection, user_id, key, fingerprint, row['id'])
    return place_data(row)


def update(request, place_id, body):
    with database() as connection:
        user_id = security.authenticated(connection, request, True)
        repository.advisory_lock(connection, 'routine-write:' + str(user_id))
        row = repository.find_place_for_update(connection, parsed_id(place_id), user_id)
        if not row:
            missing()
        if row['version'] != body.expected_version:
            raise AuthError(409, 'VERSION_CONFLICT', '장소가 변경됐어요. 최신 위치를 다시 확인해주세요.')
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
            row = repository.update_place(connection, (latitude, longitude, source, address, note, label,
                                                       int(location_changed), row['id'], user_id))
        if location_changed:
            repository.mark_routines_needs_attention(connection, user_id, row['id'])
    return place_data(row)


def delete(request, place_id):
    with database() as connection:
        user_id = security.authenticated(connection, request, True)
        repository.advisory_lock(connection, 'routine-write:' + str(user_id))
        row = repository.find_place_for_update(connection, parsed_id(place_id), user_id)
        if not row:
            missing()
        # Routines keep their route history but wait for repair after the place is gone (F06-04).
        repository.detach_routines_from_place(connection, user_id, row['id'])
        # FK SET NULL retains only the bounded retry marker, preventing late creation retries.
        repository.delete_place(connection, row['id'], user_id)


def listing(request, limit, cursor):
    with database() as connection:
        user_id = security.authenticated(connection, request)
        cursor_id = parsed_id(cursor) if cursor is not None else None
        if cursor_id and not repository.find_place_id(connection, cursor_id, user_id):
            missing()
        rows = repository.list_places(connection, user_id, cursor_id, limit)
    return {'items': [place_data(row) for row in rows[:limit]],
            'next_cursor': str(rows[limit-1]['id']) if len(rows) > limit else None}


def detail(request, place_id):
    with database() as connection:
        user_id = security.authenticated(connection, request)
        row = repository.find_place(connection, parsed_id(place_id), user_id)
        if not row:
            missing()
    return place_data(row)
