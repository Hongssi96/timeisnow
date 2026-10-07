"""Named commute routines saved from owned journey searches. Never log names or references."""
from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Request
from psycopg.types.json import Jsonb
from pydantic import BaseModel, ConfigDict, StringConstraints, model_validator

from app import auth, journey_models, places

router = APIRouter(prefix='/api/v1')


class RoutineInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=30)]
    origin_place_id: UUID
    destination_place_id: UUID
    search_id: UUID
    candidate_id: UUID

    @model_validator(mode='after')
    def distinct_places(self):
        if self.origin_place_id == self.destination_place_id:
            raise ValueError('Same origin and destination place')
        return self


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


@router.post('/routines', status_code=201)
def create(request: Request, body: RoutineInput):
    key = request.headers.get('idempotency-key')
    if key is not None and not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', key):
        raise auth.AuthError(422, 'VALIDATION_ERROR', '요청 키를 확인해주세요.')
    fingerprint = hashlib.sha256(json.dumps(body.model_dump(mode='json'), sort_keys=True).encode()).hexdigest()
    with auth.database() as connection:
        user_id = places.authenticated(connection, request, True)
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
        search = checked_search(connection, user_id, body.search_id)
        stored = next((item for item in search['candidates']
                       if isinstance(item, dict) and item.get('candidate_id') == str(body.candidate_id)), None)
        if not stored:
            raise missing_candidate()
        # Store the upgraded coordinate-free snapshot; search rows are deleted after a day.
        snapshot = journey_models.common_candidate(stored)
        refs = {ref['place_id']: ref['location_version'] for ref in search['place_refs']}
        origin = checked_place(connection, user_id, refs, body.origin_place_id)
        destination = checked_place(connection, user_id, refs, body.destination_place_id)
        connection.execute('''INSERT INTO journey_plans(id,user_id,search_id,candidate_id,candidate,total_seconds,transfer_count,model_version)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (user_id,search_id,candidate_id) DO NOTHING''',
            (uuid4(), user_id, body.search_id, body.candidate_id, Jsonb(snapshot),
             snapshot['total_seconds'], snapshot['transfer_count'], snapshot['model_version']))
        plan = connection.execute('SELECT * FROM journey_plans WHERE user_id=%s AND search_id=%s AND candidate_id=%s',
                                  (user_id, body.search_id, body.candidate_id)).fetchone()
        row = connection.execute('''INSERT INTO routines(id,user_id,name,origin_place_id,destination_place_id,journey_plan_id)
            VALUES(%s,%s,%s,%s,%s,%s) RETURNING *''',
            (uuid4(), user_id, body.name, origin['id'], destination['id'], plan['id'])).fetchone()
        if key:
            connection.execute("INSERT INTO routine_creation_keys VALUES(%s,%s,%s,%s,now()+interval '24 hours')",
                               (user_id, key, fingerprint, row['id']))
        data = response_data(connection, row)
    return auth.answer(request, data, 201)


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
