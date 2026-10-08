"""Routine business rules: route snapshot selection, schedule updates and listing."""
from datetime import datetime, timezone
import hashlib
import json
import re
from uuid import UUID, uuid4

from psycopg.types.json import Jsonb

from app.auth import security
from app.common.database import database
from app.common.errors import AuthError
from app.common.timeutil import iso
from app.journeys.models import common_candidate
from app.places.service import parsed_id as place_parsed_id
from app.routines import repository
from app.routines.dto import target_time_value


def arrival_text(value):
    return None if value is None else f'{value:%H:%M}'


def missing_search():
    raise AuthError(404, 'RESOURCE_NOT_FOUND', '루틴으로 저장할 경로 검색 결과가 없거나 만료됐어요. 경로를 다시 조회해주세요.')


def missing_candidate():
    raise AuthError(404, 'RESOURCE_NOT_FOUND', '선택한 경로 후보를 찾을 수 없어요. 경로를 다시 조회해주세요.')


def missing_place():
    raise AuthError(404, 'RESOURCE_NOT_FOUND', '루틴의 출발·도착 장소를 찾을 수 없어요. 장소를 다시 선택해주세요.')


def missing_routine():
    raise AuthError(404, 'RESOURCE_NOT_FOUND', '루틴을 찾을 수 없어요. 이미 삭제됐거나 다른 회원의 루틴이에요.')


def place_summary(row):
    if row is None:
        return None
    return {'place_id': str(row['id']), 'label': row['label'], 'name': row['name'], 'address': row['address']}


def response_data(connection, row):
    origin = destination = None
    if row['origin_place_id']:
        origin = repository.find_owned_place(connection, row['origin_place_id'], row['user_id'])
    if row['destination_place_id']:
        destination = repository.find_owned_place(connection, row['destination_place_id'], row['user_id'])
    plan = repository.find_plan(connection, row['journey_plan_id'])
    return {'routine_id': str(row['id']), 'name': row['name'],
            'origin_place': place_summary(origin), 'destination_place': place_summary(destination),
            'route': {'journey_plan_id': str(plan['id']), 'type': plan['candidate']['type'],
                      'total_seconds': plan['total_seconds'], 'transfer_count': plan['transfer_count']},
            'weekdays': list(row['weekdays']), 'target_arrival_local_time': arrival_text(row['target_arrival_local_time']),
            'timezone': row['timezone'],
            'status': row['status'], 'version': row['version'],
            'created_at': iso(row['created_at']), 'updated_at': iso(row['updated_at'])}


def checked_search(connection, user_id, search_id):
    row = repository.find_journey_search(connection, search_id, user_id)
    if not row or row['status'] != 'succeeded' or row['expires_at'] <= datetime.now(timezone.utc):
        raise missing_search()
    return row


def checked_place(connection, user_id, refs, place_id):
    row = repository.find_owned_place_for_share(connection, place_id, user_id)
    if not row:
        missing_place()
    # The saved route only matches the places as they were during this search.
    reference = refs.get(str(row['id']))
    if reference is None:
        raise AuthError(422, 'VALIDATION_ERROR', '선택한 장소가 이 경로 검색과 일치하지 않아요. 경로를 다시 조회해주세요.')
    if reference != row['location_version']:
        raise AuthError(409, 'VERSION_CONFLICT', '장소 위치가 변경됐어요. 경로를 다시 조회해주세요.')
    return row


def selected_plan(connection, user_id, body):
    search = checked_search(connection, user_id, body.search_id)
    stored = next((item for item in search['candidates']
                   if isinstance(item, dict) and item.get('candidate_id') == str(body.candidate_id)), None)
    if not stored:
        raise missing_candidate()
    # Store the upgraded coordinate-free snapshot; search rows are deleted after a day.
    snapshot = common_candidate(stored)
    if [ref['place_id'] for ref in search['place_refs']] != [str(body.origin_place_id), str(body.destination_place_id)]:
        raise AuthError(422, 'VALIDATION_ERROR', '출발·도착 장소와 경로 방향이 일치하지 않아요. 경로를 다시 조회해주세요.')
    refs = {ref['place_id']: ref['location_version'] for ref in search['place_refs']}
    origin = checked_place(connection, user_id, refs, body.origin_place_id)
    destination = checked_place(connection, user_id, refs, body.destination_place_id)
    repository.insert_plan(connection, (uuid4(), user_id, body.search_id, body.candidate_id, Jsonb(snapshot),
                                        snapshot['total_seconds'], snapshot['transfer_count'], snapshot['model_version']))
    plan = repository.find_plan_for_update(connection, user_id, body.search_id, body.candidate_id)
    return origin, destination, plan


def remove_unused_plan(connection, plan_id):
    repository.lock_plan(connection, plan_id)
    repository.delete_plan_if_unused(connection, plan_id)


def create(request, body):
    key = request.headers.get('idempotency-key')
    if key is not None and not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', key):
        raise AuthError(422, 'VALIDATION_ERROR', '요청 키를 확인해주세요.')
    fingerprint = hashlib.sha256(json.dumps(body.model_dump(mode='json'), sort_keys=True).encode()).hexdigest()
    with database() as connection:
        user_id = security.authenticated(connection, request, True)
        repository.advisory_lock(connection, 'routine-write:' + str(user_id))
        repository.delete_expired_creation_keys(connection)
        if key:
            repository.advisory_lock(connection, str(user_id) + ':' + key)
            previous = repository.find_creation_key(connection, user_id, key)
            if previous:
                if previous['body_hash'] != fingerprint:
                    raise AuthError(409, 'IDEMPOTENCY_CONFLICT', '다른 저장 요청이에요. 다시 확인해주세요.')
                # A deleted routine keeps its retry marker for 24 hours, like places.
                if previous['routine_id'] is None:
                    missing_routine()
                row = repository.find_routine(connection, previous['routine_id'], user_id)
                if not row:
                    missing_routine()
                return response_data(connection, row)
        origin, destination, plan = selected_plan(connection, user_id, body)
        row = repository.insert_routine(connection, (uuid4(), user_id, body.name, origin['id'], destination['id'], plan['id'],
                                                     body.weekdays, target_time_value(body.target_arrival_local_time)))
        if key:
            repository.insert_creation_key(connection, (user_id, key, fingerprint, row['id']))
        data = response_data(connection, row)
    return data


def listing(request, limit, cursor):
    with database() as connection:
        user_id = security.authenticated(connection, request)
        try:
            cursor_id = UUID(cursor) if cursor is not None else None
        except ValueError:
            raise AuthError(422, 'VALIDATION_ERROR', '목록 조회 위치를 확인해주세요.') from None
        cursor_time = None
        if cursor_id:
            boundary = repository.find_routine_created_at(connection, cursor_id, user_id)
            if not boundary:
                missing_routine()
            cursor_time = boundary['created_at']
        rows = repository.list_routines(connection, user_id, cursor_id, cursor_time, limit)
        data = {'items': [response_data(connection, row) for row in rows[:limit]],
                'next_cursor': str(rows[limit - 1]['id']) if len(rows) > limit else None}
    return data


def detail(request, routine_id):
    with database() as connection:
        user_id = security.authenticated(connection, request)
        row = repository.find_routine(connection, place_parsed_id(routine_id), user_id)
        if not row:
            missing_routine()
        data = response_data(connection, row)
    return data


def update(request, routine_id, body):
    with database() as connection:
        user_id = security.authenticated(connection, request, True)
        repository.advisory_lock(connection, 'routine-write:' + str(user_id))
        row = repository.find_routine_for_update(connection, place_parsed_id(routine_id), user_id)
        if not row:
            missing_routine()
        if body.expected_version != row['version']:
            raise AuthError(409, 'VERSION_CONFLICT', '루틴이 다른 화면에서 변경됐어요. 새로 확인해주세요.')
        weekdays = row['weekdays'] if body.weekdays is None else list(body.weekdays)
        target = row['target_arrival_local_time']
        if 'target_arrival_local_time' in body.model_fields_set:
            target = target_time_value(body.target_arrival_local_time)
        name = row['name'] if body.name is None else body.name
        origin_id, destination_id, plan_id, status = (row['origin_place_id'], row['destination_place_id'],
                                                     row['journey_plan_id'], row['status'])
        if 'search_id' in body.model_fields_set:
            origin, destination, plan = selected_plan(connection, user_id, body)
            origin_id, destination_id, plan_id, status = origin['id'], destination['id'], plan['id'], 'active'
        updated = repository.update_routine(connection, (name, weekdays, target, origin_id, destination_id, plan_id, status, row['id']))
        if plan_id != row['journey_plan_id']:
            remove_unused_plan(connection, row['journey_plan_id'])
        data = response_data(connection, updated)
    return data


def delete(request, routine_id):
    with database() as connection:
        user_id = security.authenticated(connection, request, True)
        repository.advisory_lock(connection, 'routine-write:' + str(user_id))
        row = repository.find_routine_for_update(connection, place_parsed_id(routine_id), user_id)
        if not row:
            missing_routine()
        repository.delete_routine(connection, row['id'], user_id)
        remove_unused_plan(connection, row['journey_plan_id'])
