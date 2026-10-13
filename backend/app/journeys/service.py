"""Journey admission, safe retries and the background worker."""
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import re
from uuid import uuid4

from psycopg.types.json import Jsonb

from app.auth import security
from app.arrivals import cache as arrival_cache
from app.common.database import database
from app.common.errors import AuthError
from app.common.response import answer
from app.common.timeutil import iso
from app.journeys import provider, repository
from app.journeys.models import common_candidate
from app.origins.dto import SavedOrigin
from app.places import provider as places_provider
from app.places.dto import Location
from app.places.service import missing as place_missing, parsed_id as place_parsed_id


def missing():
    raise AuthError(404, 'RESOURCE_NOT_FOUND', '경로 검색 결과를 찾을 수 없어요. 다시 검색해주세요.')


def check_refs(connection, user_id, refs):
    for ref in refs:
        row = repository.find_place_version_for_share(connection, place_parsed_id(ref['place_id']), user_id)
        if not row: missing()
        if row['location_version'] != ref['location_version']:
            raise AuthError(409, 'VERSION_CONFLICT', '장소 위치가 변경됐어요. 다시 검색해주세요.')


def resolve(connection, user_id, endpoint, refs):
    if isinstance(endpoint, SavedOrigin):
        row = repository.find_owned_place_for_share(connection, place_parsed_id(endpoint.place_id), user_id)
        if not row: missing()
        if endpoint.location_version is not None and row['location_version'] != endpoint.location_version:
            raise AuthError(409, 'VERSION_CONFLICT', '장소 위치가 변경됐어요. 다시 검색해주세요.')
        refs.append({'place_id':str(row['id']),'location_version':row['location_version']})
        return Location(latitude=row['latitude'],longitude=row['longitude'])
    return Location(latitude=endpoint.latitude,longitude=endpoint.longitude)


def cleanup(connection):
    # Safe worker expiry/restart behavior: no replay of device coordinates.
    repository.fail_interrupted_workers(connection, Jsonb({'code':'JOB_INTERRUPTED','message':'경로 검색이 중단됐어요. 다시 검색해주세요.','details':[]}))
    repository.expire_stored_candidates(connection)
    repository.delete_expired_keys(connection)
    repository.delete_expired_searches(connection)


def replay(connection, request, previous, user_id, fingerprint):
    if previous['body_hash'] != fingerprint:
        raise AuthError(409,'IDEMPOTENCY_CONFLICT','다른 입력에는 새 요청 키를 사용해주세요.')
    row = repository.find_search(connection, previous['search_id'], user_id)
    if not row or row['expires_at'] <= datetime.now(timezone.utc): missing()
    check_refs(connection,user_id,row['place_refs'])
    return answer(request,{'search_id':str(row['id']),'job_id':str(row['job_id']),'status':'queued'},202)


def execute(search_id, user_id, start, end, preference):
    contexts={}
    try:
        with database() as connection:
            row = repository.claim_queued(connection, search_id)
            if not row: return
            owner = repository.find_user_status(connection, user_id)
            if not owner or owner['status'] != 'active': missing()
            check_refs(connection,user_id,row['place_refs'])
        places_provider.region_for_location(start); places_provider.region_for_location(end)
        candidates, reasons = provider.normalize(provider.fetch_routes(start,end),preference,mapping_contexts=contexts)
        error = None
    except AuthError as exception:
        candidates, reasons = [], []
        error = {'code':exception.code,'message':exception.message,'details':[]}
    except Exception:
        candidates, reasons = [], []
        error = {'code':'INTERNAL_ERROR','message':'경로 검색을 완료할 수 없어요.','details':[]}
    try:
        with database() as connection:
            row = repository.find_search_for_update(connection, search_id)
            if not row or row['status'] not in ('queued','running'): return
            now = datetime.now(timezone.utc)
            if row['worker_deadline'] <= now:
                error = {'code':'JOB_INTERRUPTED','message':'경로 검색이 중단됐어요. 다시 검색해주세요.','details':[]}
            elif not error:
                try:
                    owner = repository.find_user_status(connection, user_id)
                    if not owner or owner['status'] != 'active': missing()
                    check_refs(connection,user_id,row['place_refs'])
                except AuthError as exception:
                    error = {'code':exception.code,'message':exception.message,'details':[]}
            if error or row['expires_at'] <= now: candidates = []
            repository.finish_search(connection,('failed' if error else 'succeeded',Jsonb(candidates),Jsonb(reasons),Jsonb(error) if error else None,search_id))
        if not error and candidates:
            arrival_cache.publish(user_id,search_id,candidates,contexts,row['expires_at'])
    except Exception:
        # Failed DB writes leave a lease that becomes JOB_INTERRUPTED; never log input.
        return


def search(request, body):
    """Returns ('replay', response) or ('queued', data, execute_task_args)."""
    key = request.headers.get('idempotency-key')
    if key is not None and not re.fullmatch(r'[A-Za-z0-9_-]{1,128}',key):
        raise AuthError(422,'VALIDATION_ERROR','요청 키를 확인해주세요.')
    if body.timing.mode != 'depart_now':
        raise AuthError(422,'UNSUPPORTED_TIMING','목표 도착 시각 검색은 준비 중이에요.')
    if body.timing.arrive_by is not None:
        raise AuthError(422,'VALIDATION_ERROR','현재 출발 검색에는 목표 도착 시각을 넣지 않아요.')
    with database() as connection:
        user_id = security.authenticated(connection,request,True)
        _, secret, _ = security.settings()
        fingerprint = hmac.new(secret,json.dumps(body.model_dump(mode='json'),sort_keys=True,separators=(',',':')).encode(),hashlib.sha256).hexdigest()
        # Serialize admissions across processes, including quota and retry races.
        repository.admission_lock(connection)
        cleanup(connection)
        if key:
            previous = repository.find_search_key(connection,user_id,key)
            if previous:
                return 'replay', replay(connection,request,previous,user_id,fingerprint)
        security.increment(connection,security.bucket(connection,'journey-search',str(user_id),60,10,secret))
    # Quota stays committed even for invalid ownership or admission/provider failure.
    with database() as connection:
        security.authenticated(connection,request,True)
        repository.admission_lock(connection)
        cleanup(connection)
        # Another admitted request can have committed the same key in between transactions.
        previous = repository.find_search_key(connection,user_id,key) if key else None
        if previous: return 'replay', replay(connection,request,previous,user_id,fingerprint)
        active = repository.active_counts(connection,user_id)
        if active['total'] >= 8 or active['owned'] >= 2:
            raise AuthError(429,'RATE_LIMITED','진행 중인 경로 검색을 기다려주세요.',{'Retry-After':'2'})
        refs = []
        start,end = resolve(connection,user_id,body.origin,refs),resolve(connection,user_id,body.destination,refs)
        preference = body.preferences.route_preference if body.preferences else repository.find_user_profile_preference(connection,user_id)['route_preference']
        search_id,job_id,now = uuid4(),uuid4(),datetime.now(timezone.utc)
        repository.insert_search(connection,(search_id,job_id,user_id,Jsonb(refs),now+timedelta(seconds=300),now+timedelta(seconds=60),now+timedelta(days=1)))
        if key:
            repository.insert_search_key(connection,(user_id,key,fingerprint,search_id,now+timedelta(days=1)))
    return 'queued', {'search_id':str(search_id),'job_id':str(job_id),'status':'queued'}, (search_id,user_id,start,end,preference)


def owned(request, identifier, job=False):
    with database() as connection:
        user_id = security.authenticated(connection,request)
        cleanup(connection)
    with database() as connection:
        security.authenticated(connection,request)
        column = 'job_id' if job else 'id'
        row = repository.find_search_by_column(connection,column,place_parsed_id(identifier),user_id)
        if not row or (not job and row['expires_at'] <= datetime.now(timezone.utc)): missing()
        if not job: check_refs(connection,user_id,row['place_refs'])
        return row


def result(request, search_id):
    row = owned(request,search_id)
    if not isinstance(row['candidates'],list) or len(row['candidates']) > 20:
        raise AuthError(502,'PROVIDER_RESPONSE_INVALID','경로 구간을 확인할 수 없어요.')
    candidates = [common_candidate(candidate) for candidate in row['candidates']]
    reasons = list(dict.fromkeys(row['unavailable_reasons'] + [reason for candidate in candidates for reason in candidate['missing_segments']]))
    response = answer(request,{'search_id':str(row['id']),'job_id':str(row['job_id']),'status':row['status'],
        'candidates':candidates,'unavailable_reasons':reasons,'error':row['error'],'expires_at':iso(row['expires_at'])})
    if row['status'] in ('queued','running'): response.headers['Retry-After'] = '2'
    return response


def job_result(request, job_id):
    row = owned(request,job_id,True)
    expired = row['expires_at'] <= datetime.now(timezone.utc)
    response = answer(request,{'job_id':str(row['job_id']),'status':row['status'],'error':row['error'],
        'result_ref':f"/api/v1/journey-searches/{row['id']}" if row['status'] == 'succeeded' and not expired else None,
        'finished_at':iso(row['finished_at']) if row['finished_at'] else None,
        'expires_at':iso(row['job_expires_at']),'result_expired':expired})
    if row['status'] in ('queued','running'): response.headers['Retry-After'] = '2'
    return response
