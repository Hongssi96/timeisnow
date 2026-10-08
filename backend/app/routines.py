"""Named commute routines saved from owned journey searches. Never log names or references."""
from datetime import datetime, time, timezone
import hashlib
import json
import re
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Query, Request
from fastapi.responses import Response
from psycopg.types.json import Jsonb
from pydantic import BaseModel, ConfigDict, StringConstraints, StrictInt, model_validator

from app import auth, journey_models, places

router = APIRouter(prefix='/api/v1')

# ISO-8601 weekday numbers: 1=Monday ... 7=Sunday, Asia/Seoul.
WEEKDAY_LIMITS = range(1, 8)
ARRIVAL_TIME = re.compile(r'([01]\d|2[0-3]):([0-5]\d)$')


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


def checked_weekdays(values):
    if not values or len(values) > 7 or len(set(values)) != len(values) \
            or any(value not in WEEKDAY_LIMITS for value in values):
        raise auth.AuthError(422, 'VALIDATION_ERROR', '요일은 월(1)부터 일(7)까지 숫자로 중복 없이 1개 이상 보내주세요.')


def target_time_value(value):
    if value is None:
        return None
    match = ARRIVAL_TIME.fullmatch(value)
    if not match:
        raise auth.AuthError(422, 'VALIDATION_ERROR', '목표 도착 시각은 HH:MM 형식으로 보내주세요.')
    return time(int(match.group(1)), int(match.group(2)))


def arrival_text(value):
    return None if value is None else f'{value:%H:%M}'


def missing_search():
    raise auth.AuthError(404, 'RESOURCE_NOT_FOUND', '루틴으로 저장할 경로 검색 결과가 없거나 만료됐어요. 경로를 다시 조회해주세요.')


def missing_candidate():
    raise auth.AuthError(404, 'RESOURCE_NOT_FOUND', '선택한 경로 후보를 찾을 수 없어요. 경로를 다시 조회해주세요.')


def missing_place():
    raise auth.AuthError(404, 'RESOURCE_NOT_FOUND', '루틴의 출발·도착 장소를 찾을 수 없어요. 장소를 다시 선택해주세요.')


def missing_routine():
    raise auth.AuthError(404, 'RESOURCE_NOT_FOUND', '루틴을 찾을 수 없어요. 이미 삭제됐거나 다른 회원의 루틴이에요.')


def place_summary(row):
    if row is None:
        return None
    return {'place_id': str(row['id']), 'label': row['label'], 'name': row['name'], 'address': row['address']}


def response_data(connection, row):
    origin = destination = None
    if row['origin_place_id']:
        origin = connection.execute('SELECT * FROM saved_places WHERE id=%s AND user_id=%s',
                                    (row['origin_place_id'], row['user_id'])).fetchone()
    if row['destination_place_id']:
        destination = connection.execute('SELECT * FROM saved_places WHERE id=%s AND user_id=%s',
                                         (row['destination_place_id'], row['user_id'])).fetchone()
    plan = connection.execute('SELECT * FROM journey_plans WHERE id=%s', (row['journey_plan_id'],)).fetchone()
    return {'routine_id': str(row['id']), 'name': row['name'],
            'origin_place': place_summary(origin), 'destination_place': place_summary(destination),
            'route': {'journey_plan_id': str(plan['id']), 'type': plan['candidate']['type'],
                      'total_seconds': plan['total_seconds'], 'transfer_count': plan['transfer_count']},
            'weekdays': list(row['weekdays']), 'target_arrival_local_time': arrival_text(row['target_arrival_local_time']),
            'timezone': row['timezone'],
            'status': row['status'], 'version': row['version'],
            'created_at': auth.iso(row['created_at']), 'updated_at': auth.iso(row['updated_at'])}


def checked_search(connection, user_id, search_id):
    row = connection.execute('SELECT * FROM journey_searches WHERE id=%s AND user_id=%s',
                             (search_id, user_id)).fetchone()
    if not row or row['status'] != 'succeeded' or row['expires_at'] <= datetime.now(timezone.utc):
        raise missing_search()
    return row


def checked_place(connection, user_id, refs, place_id):
    row = connection.execute('SELECT * FROM saved_places WHERE id=%s AND user_id=%s FOR SHARE',
                             (place_id, user_id)).fetchone()
    if not row:
        raise missing_place()
    # The saved route only matches the places as they were during this search.
    reference = refs.get(str(row['id']))
    if reference is None:
        raise auth.AuthError(422, 'VALIDATION_ERROR', '선택한 장소가 이 경로 검색과 일치하지 않아요. 경로를 다시 조회해주세요.')
    if reference != row['location_version']:
        raise auth.AuthError(409, 'VERSION_CONFLICT', '장소 위치가 변경됐어요. 경로를 다시 조회해주세요.')
    return row


def selected_plan(connection, user_id, body):
    search = checked_search(connection, user_id, body.search_id)
    stored = next((item for item in search['candidates']
                   if isinstance(item, dict) and item.get('candidate_id') == str(body.candidate_id)), None)
    if not stored:
        raise missing_candidate()
    # Store the upgraded coordinate-free snapshot; search rows are deleted after a day.
    snapshot = journey_models.common_candidate(stored)
    if [ref['place_id'] for ref in search['place_refs']] != [str(body.origin_place_id), str(body.destination_place_id)]:
        raise auth.AuthError(422, 'VALIDATION_ERROR', '출발·도착 장소와 경로 방향이 일치하지 않아요. 경로를 다시 조회해주세요.')
    refs = {ref['place_id']: ref['location_version'] for ref in search['place_refs']}
    origin = checked_place(connection, user_id, refs, body.origin_place_id)
    destination = checked_place(connection, user_id, refs, body.destination_place_id)
    connection.execute('''INSERT INTO journey_plans(id,user_id,search_id,candidate_id,candidate,total_seconds,transfer_count,model_version)
        VALUES(%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (user_id,search_id,candidate_id) DO NOTHING''',
        (uuid4(), user_id, body.search_id, body.candidate_id, Jsonb(snapshot),
         snapshot['total_seconds'], snapshot['transfer_count'], snapshot['model_version']))
    plan = connection.execute('SELECT * FROM journey_plans WHERE user_id=%s AND search_id=%s AND candidate_id=%s FOR UPDATE',
                              (user_id, body.search_id, body.candidate_id)).fetchone()
    return origin, destination, plan


@router.post('/routines', status_code=201)
def create(request: Request, body: RoutineInput):
    key = request.headers.get('idempotency-key')
    if key is not None and not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', key):
        raise auth.AuthError(422, 'VALIDATION_ERROR', '요청 키를 확인해주세요.')
    fingerprint = hashlib.sha256(json.dumps(body.model_dump(mode='json'), sort_keys=True).encode()).hexdigest()
    with auth.database() as connection:
        user_id = places.authenticated(connection, request, True)
        connection.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))', ('routine-write:' + str(user_id),))
        connection.execute('DELETE FROM routine_creation_keys WHERE expires_at <= now()')
        if key:
            connection.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))', (str(user_id) + ':' + key,))
            previous = connection.execute('SELECT * FROM routine_creation_keys WHERE user_id=%s AND key=%s',
                                          (user_id, key)).fetchone()
            if previous:
                if previous['body_hash'] != fingerprint:
                    raise auth.AuthError(409, 'IDEMPOTENCY_CONFLICT', '다른 저장 요청이에요. 다시 확인해주세요.')
                # A deleted routine keeps its retry marker for 24 hours, like places.
                if previous['routine_id'] is None:
                    raise missing_routine()
                row = connection.execute('SELECT * FROM routines WHERE id=%s AND user_id=%s',
                                         (previous['routine_id'], user_id)).fetchone()
                if not row:
                    raise missing_routine()
                return auth.answer(request, response_data(connection, row), 201)
        origin, destination, plan = selected_plan(connection, user_id, body)
        row = connection.execute('''INSERT INTO routines(id,user_id,name,origin_place_id,destination_place_id,journey_plan_id,
            weekdays,target_arrival_local_time)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *''',
            (uuid4(), user_id, body.name, origin['id'], destination['id'], plan['id'],
             body.weekdays, target_time_value(body.target_arrival_local_time))).fetchone()
        if key:
            connection.execute("INSERT INTO routine_creation_keys VALUES(%s,%s,%s,%s,now()+interval '24 hours')",
                               (user_id, key, fingerprint, row['id']))
        data = response_data(connection, row)
    return auth.answer(request, data, 201)


@router.get('/routines')
def listing(request: Request, limit: int = Query(default=20, ge=1, le=100), cursor: str | None = None):
    with auth.database() as connection:
        user_id = places.authenticated(connection, request)
        try:
            cursor_id = UUID(cursor) if cursor is not None else None
        except ValueError:
            raise auth.AuthError(422, 'VALIDATION_ERROR', '목록 조회 위치를 확인해주세요.') from None
        cursor_time = None
        if cursor_id:
            boundary = connection.execute('SELECT created_at FROM routines WHERE id=%s AND user_id=%s',
                                          (cursor_id, user_id)).fetchone()
            if not boundary:
                raise missing_routine()
            cursor_time = boundary['created_at']
        rows = connection.execute("""SELECT * FROM routines WHERE user_id=%s
            AND (%s::uuid IS NULL OR (created_at,id) < (%s::timestamptz,%s::uuid))
            ORDER BY created_at DESC,id DESC LIMIT %s""",
            (user_id, cursor_id, cursor_time, cursor_id, limit + 1)).fetchall()
        data = {'items': [response_data(connection, row) for row in rows[:limit]],
                'next_cursor': str(rows[limit - 1]['id']) if len(rows) > limit else None}
    return auth.answer(request, data)


@router.get('/routines/{routine_id}')
def detail(request: Request, routine_id: str):
    with auth.database() as connection:
        user_id = places.authenticated(connection, request)
        row = connection.execute('SELECT * FROM routines WHERE id=%s AND user_id=%s',
                                 (places.parsed_id(routine_id), user_id)).fetchone()
        if not row:
            raise missing_routine()
        data = response_data(connection, row)
    return auth.answer(request, data)


@router.patch('/routines/{routine_id}')
def update(request: Request, routine_id: str, body: RoutineScheduleInput):
    with auth.database() as connection:
        user_id = places.authenticated(connection, request, True)
        connection.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))', ('routine-write:' + str(user_id),))
        row = connection.execute('SELECT * FROM routines WHERE id=%s AND user_id=%s FOR UPDATE',
                                 (places.parsed_id(routine_id), user_id)).fetchone()
        if not row:
            raise missing_routine()
        if body.expected_version != row['version']:
            raise auth.AuthError(409, 'VERSION_CONFLICT', '루틴이 다른 화면에서 변경됐어요. 새로 확인해주세요.')
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
        updated = connection.execute('''UPDATE routines SET name=%s, weekdays=%s, target_arrival_local_time=%s,
            origin_place_id=%s, destination_place_id=%s, journey_plan_id=%s, status=%s,
            version=version+1, updated_at=now() WHERE id=%s RETURNING *''',
            (name, weekdays, target, origin_id, destination_id, plan_id, status, row['id'])).fetchone()
        if plan_id != row['journey_plan_id']:
            remove_unused_plan(connection, row['journey_plan_id'])
        data = response_data(connection, updated)
    return auth.answer(request, data)


def remove_unused_plan(connection, plan_id):
    connection.execute('SELECT id FROM journey_plans WHERE id=%s FOR UPDATE', (plan_id,))
    connection.execute('DELETE FROM journey_plans WHERE id=%s AND NOT EXISTS '
                       '(SELECT 1 FROM routines WHERE journey_plan_id=%s)', (plan_id, plan_id))


@router.delete('/routines/{routine_id}')
def delete(request: Request, routine_id: str):
    with auth.database() as connection:
        user_id = places.authenticated(connection, request, True)
        connection.execute('SELECT pg_advisory_xact_lock(hashtextextended(%s,0))', ('routine-write:' + str(user_id),))
        row = connection.execute('SELECT * FROM routines WHERE id=%s AND user_id=%s FOR UPDATE',
                                 (places.parsed_id(routine_id), user_id)).fetchone()
        if not row:
            raise missing_routine()
        connection.execute('DELETE FROM routines WHERE id=%s AND user_id=%s', (row['id'], user_id))
        remove_unused_plan(connection, row['journey_plan_id'])
    return Response(status_code=204, headers={'Cache-Control': 'no-store'})
