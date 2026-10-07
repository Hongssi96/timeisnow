"""Owned asynchronous journey lookup with bounded state and safe retries."""
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import re
from typing import Annotated, Literal
from uuid import uuid4
from fastapi import APIRouter, BackgroundTasks, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator
from psycopg.types.json import Jsonb
from app import auth, origins, places, journey_provider

router = APIRouter(prefix='/api/v1')


class CurrentLocation(origins.CurrentOrigin):
    location_confirmed: bool = Field(strict=True)

    @field_validator('location_confirmed')
    @classmethod
    def confirmed(cls, value):
        if value is not True:
            raise ValueError('Manual confirmation required')
        return value


Endpoint = Annotated[CurrentLocation | origins.MapOrigin | origins.SavedOrigin, Field(discriminator='type')]


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


def missing():
    raise auth.AuthError(404, 'RESOURCE_NOT_FOUND', '경로 검색 결과를 찾을 수 없어요. 다시 검색해주세요.')


def check_refs(connection, user_id, refs):
    for ref in refs:
        row = connection.execute('SELECT location_version FROM saved_places WHERE id=%s AND user_id=%s FOR SHARE',
                                 (places.parsed_id(ref['place_id']), user_id)).fetchone()
        if not row: missing()
        if row['location_version'] != ref['location_version']:
            raise auth.AuthError(409, 'VERSION_CONFLICT', '장소 위치가 변경됐어요. 다시 검색해주세요.')


def resolve(connection, user_id, endpoint, refs):
    if isinstance(endpoint, origins.SavedOrigin):
        row = connection.execute('SELECT * FROM saved_places WHERE id=%s AND user_id=%s FOR SHARE',
                                 (places.parsed_id(endpoint.place_id), user_id)).fetchone()
        if not row: missing()
        if endpoint.location_version is not None and row['location_version'] != endpoint.location_version:
            raise auth.AuthError(409, 'VERSION_CONFLICT', '장소 위치가 변경됐어요. 다시 검색해주세요.')
        refs.append({'place_id':str(row['id']),'location_version':row['location_version']})
        return places.Location(latitude=row['latitude'],longitude=row['longitude'])
    return places.Location(latitude=endpoint.latitude,longitude=endpoint.longitude)


def cleanup(connection):
    # Safe worker expiry/restart behavior: no replay of device coordinates.
    error = Jsonb({'code':'JOB_INTERRUPTED','message':'경로 검색이 중단됐어요. 다시 검색해주세요.','details':[]})
    connection.execute("""UPDATE journey_searches SET status='failed',error=%s,finished_at=now(),job_expires_at=now()+interval '24 hours'
        WHERE status IN ('queued','running') AND worker_deadline <= now()""", (error,))
    connection.execute("UPDATE journey_searches SET candidates='[]',unavailable_reasons='[]' WHERE expires_at <= now() AND (candidates <> '[]' OR unavailable_reasons <> '[]')")
    connection.execute('DELETE FROM journey_search_keys WHERE expires_at <= now()')
    connection.execute('DELETE FROM journey_searches WHERE job_expires_at <= now()')


def replay(connection, request, previous, user_id, fingerprint):
    if previous['body_hash'] != fingerprint:
        raise auth.AuthError(409,'IDEMPOTENCY_CONFLICT','다른 입력에는 새 요청 키를 사용해주세요.')
    row = connection.execute('SELECT * FROM journey_searches WHERE id=%s AND user_id=%s',(previous['search_id'],user_id)).fetchone()
    if not row or row['expires_at'] <= datetime.now(timezone.utc): missing()
    check_refs(connection,user_id,row['place_refs'])
    return auth.answer(request,{'search_id':str(row['id']),'job_id':str(row['job_id']),'status':'queued'},202)


def execute(search_id, user_id, start, end, preference):
    try:
        with auth.database() as connection:
            row = connection.execute("UPDATE journey_searches SET status='running' WHERE id=%s AND status='queued' AND worker_deadline>now() RETURNING *",(search_id,)).fetchone()
            if not row: return
            owner = connection.execute('SELECT status FROM users WHERE id=%s',(user_id,)).fetchone()
            if not owner or owner['status'] != 'active': missing()
            check_refs(connection,user_id,row['place_refs'])
        places.region_for_location(start); places.region_for_location(end)
        candidates, reasons = journey_provider.normalize(journey_provider.fetch_routes(start,end),preference)
        error = None
    except auth.AuthError as exception:
        candidates, reasons = [], []
        error = {'code':exception.code,'message':exception.message,'details':[]}
    except Exception:
        candidates, reasons = [], []
        error = {'code':'INTERNAL_ERROR','message':'경로 검색을 완료할 수 없어요.','details':[]}
    try:
        with auth.database() as connection:
            row = connection.execute('SELECT * FROM journey_searches WHERE id=%s FOR UPDATE',(search_id,)).fetchone()
            if not row or row['status'] not in ('queued','running'): return
            now = datetime.now(timezone.utc)
            if row['worker_deadline'] <= now:
                error = {'code':'JOB_INTERRUPTED','message':'경로 검색이 중단됐어요. 다시 검색해주세요.','details':[]}
            elif not error:
                try:
                    owner = connection.execute('SELECT status FROM users WHERE id=%s',(user_id,)).fetchone()
                    if not owner or owner['status'] != 'active': missing()
                    check_refs(connection,user_id,row['place_refs'])
                except auth.AuthError as exception:
                    error = {'code':exception.code,'message':exception.message,'details':[]}
            if error or row['expires_at'] <= now: candidates = []
            connection.execute('''UPDATE journey_searches SET status=%s,candidates=%s,unavailable_reasons=%s,error=%s,
                finished_at=now(),job_expires_at=now()+interval '24 hours' WHERE id=%s''',
                ('failed' if error else 'succeeded',Jsonb(candidates),Jsonb(reasons),Jsonb(error) if error else None,search_id))
    except Exception:
        # Failed DB writes leave a lease that becomes JOB_INTERRUPTED; never log input.
        return


@router.post('/journey-searches', status_code=202)
def search(request: Request, body: SearchInput, background: BackgroundTasks):
    key = request.headers.get('idempotency-key')
    if key is not None and not re.fullmatch(r'[A-Za-z0-9_-]{1,128}',key):
        raise auth.AuthError(422,'VALIDATION_ERROR','요청 키를 확인해주세요.')
    if body.timing.mode != 'depart_now':
        raise auth.AuthError(422,'UNSUPPORTED_TIMING','목표 도착 시각 검색은 준비 중이에요.')
    if body.timing.arrive_by is not None:
        raise auth.AuthError(422,'VALIDATION_ERROR','현재 출발 검색에는 목표 도착 시각을 넣지 않아요.')
    with auth.database() as connection:
        user_id = places.authenticated(connection,request,True)
        _, secret, _ = auth.settings()
        fingerprint = hmac.new(secret,json.dumps(body.model_dump(mode='json'),sort_keys=True,separators=(',',':')).encode(),hashlib.sha256).hexdigest()
        # Serialize admissions across processes, including quota and retry races.
        connection.execute("SELECT pg_advisory_xact_lock(hashtext('journey-admission'))")
        cleanup(connection)
        if key:
            previous = connection.execute('SELECT * FROM journey_search_keys WHERE user_id=%s AND key=%s',(user_id,key)).fetchone()
            if previous:
                return replay(connection,request,previous,user_id,fingerprint)
        auth.increment(connection,auth.bucket(connection,'journey-search',str(user_id),60,10,secret))
    # Quota stays committed even for invalid ownership or admission/provider failure.
    with auth.database() as connection:
        places.authenticated(connection,request,True)
        connection.execute("SELECT pg_advisory_xact_lock(hashtext('journey-admission'))")
        cleanup(connection)
        # Another admitted request can have committed the same key in between transactions.
        previous = connection.execute('SELECT * FROM journey_search_keys WHERE user_id=%s AND key=%s',(user_id,key)).fetchone() if key else None
        if previous: return replay(connection,request,previous,user_id,fingerprint)
        active = connection.execute("SELECT count(*) AS total,count(*) FILTER (WHERE user_id=%s) AS owned FROM journey_searches WHERE status IN ('queued','running')",(user_id,)).fetchone()
        if active['total'] >= 8 or active['owned'] >= 2:
            raise auth.AuthError(429,'RATE_LIMITED','진행 중인 경로 검색을 기다려주세요.',{'Retry-After':'2'})
        refs = []
        start,end = resolve(connection,user_id,body.origin,refs),resolve(connection,user_id,body.destination,refs)
        preference = body.preferences.route_preference if body.preferences else connection.execute('SELECT route_preference FROM user_profiles WHERE user_id=%s',(user_id,)).fetchone()['route_preference']
        search_id,job_id,now = uuid4(),uuid4(),datetime.now(timezone.utc)
        connection.execute('''INSERT INTO journey_searches(id,job_id,user_id,status,place_refs,expires_at,worker_deadline,job_expires_at)
            VALUES(%s,%s,%s,'queued',%s,%s,%s,%s)''',(search_id,job_id,user_id,Jsonb(refs),now+timedelta(seconds=300),now+timedelta(seconds=60),now+timedelta(days=1)))
        if key:
            connection.execute('INSERT INTO journey_search_keys VALUES(%s,%s,%s,%s,%s)',(user_id,key,fingerprint,search_id,now+timedelta(days=1)))
    background.add_task(execute,search_id,user_id,start,end,preference)
    return auth.answer(request,{'search_id':str(search_id),'job_id':str(job_id),'status':'queued'},202)


def owned(request, identifier, job=False):
    with auth.database() as connection:
        user_id = places.authenticated(connection,request)
        cleanup(connection)
    with auth.database() as connection:
        places.authenticated(connection,request)
        column = 'job_id' if job else 'id'
        row = connection.execute(f'SELECT * FROM journey_searches WHERE {column}=%s AND user_id=%s',(places.parsed_id(identifier),user_id)).fetchone()
        if not row or (not job and row['expires_at'] <= datetime.now(timezone.utc)): missing()
        if not job: check_refs(connection,user_id,row['place_refs'])
        return row


@router.get('/journey-searches/{search_id}')
def result(request: Request, search_id: str):
    row = owned(request,search_id)
    response = auth.answer(request,{'search_id':str(row['id']),'job_id':str(row['job_id']),'status':row['status'],
        'candidates':row['candidates'],'unavailable_reasons':row['unavailable_reasons'],'error':row['error'],'expires_at':auth.iso(row['expires_at'])})
    if row['status'] in ('queued','running'): response.headers['Retry-After'] = '2'
    return response


@router.get('/jobs/{job_id}')
def job_result(request: Request, job_id: str):
    row = owned(request,job_id,True)
    expired = row['expires_at'] <= datetime.now(timezone.utc)
    response = auth.answer(request,{'job_id':str(row['job_id']),'status':row['status'],'error':row['error'],
        'result_ref':f"/api/v1/journey-searches/{row['id']}" if row['status'] == 'succeeded' and not expired else None,
        'finished_at':auth.iso(row['finished_at']) if row['finished_at'] else None,
        'expires_at':auth.iso(row['job_expires_at']),'result_expired':expired})
    if row['status'] in ('queued','running'): response.headers['Retry-After'] = '2'
    return response
