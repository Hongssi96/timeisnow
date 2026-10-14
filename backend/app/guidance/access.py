"""Missing access walk for owned routine origins and verified boarding mappings."""
from datetime import timedelta
import time
from app.arrivals import cache,service as arrivals
from app.common.database import database
from app.common.errors import AuthError
from app.routines import repository
from app.guidance import walk_provider


def place(user_id,origin_ref):
    with database() as connection:row=repository.find_owned_place(connection,arrivals.parsed_id(origin_ref[0]),user_id)
    if row is None:arrivals.missing()
    if row['location_version']!=origin_ref[1]:raise AuthError(409,'VERSION_CONFLICT','출발 장소가 변경됐어요.')
    return row


def get(user_id,search_id,candidate_id,first,snapshot,origin_ref,deadline):
    entry=cache.lookup(user_id,search_id,candidate_id,snapshot,arrivals.now())
    if entry is None or entry.mapping is None or entry.boarding_endpoint is None:return None,'ACCESS_WALK_MAPPING_REQUIRED'
    mapping=arrivals.checked_mapping(entry.mapping,first,arrivals.now())
    identity=cache.mapping_identity(mapping)
    if entry.boarding_endpoint.get('mapping_identity')!=identity:return None,'ACCESS_WALK_MAPPING_REQUIRED'
    if not entry.lock.acquire(blocking=False):raise AuthError(429,'RATE_LIMITED','접근 도보를 확인 중이에요.',{'Retry-After':'2'})
    try:
        row,_,_,fp=arrivals.owned(user_id,search_id,candidate_id)
        if fp!=snapshot:raise AuthError(409,'VERSION_CONFLICT','경로가 변경됐어요.')
        if len(row['place_refs'])!=2 or (row['place_refs'][0]['place_id'],row['place_refs'][0]['location_version'])!=origin_ref:
            raise AuthError(409,'VERSION_CONFLICT','출발 장소가 검색과 일치하지 않아요.')
        origin=place(user_id,origin_ref);cached=entry.access_walk;at=arrivals.now()
        if cached and cached['identity']==identity and cached['origin_ref']==origin_ref and at<=cached['expires_at']:
            if cached['seconds'] is not None:return cached,None
            if at-cached['fetched_at']<timedelta(seconds=60):return None,cached['reason']
        if deadline-time.monotonic()<3:return None,'ACCESS_WALK_TIME_LIMIT'
        arrivals.reserve_refresh(user_id)
        reason='ACCESS_WALK_UNAVAILABLE'
        try:seconds=walk_provider.fetch((origin['longitude'],origin['latitude']),entry.boarding_endpoint['point'],deadline)
        except AuthError as error:
            if error.code not in ('PROVIDER_TIMEOUT','PROVIDER_UNAVAILABLE','PROVIDER_RESPONSE_INVALID'):raise
            seconds=None;reason='ACCESS_WALK_TIMEOUT' if error.code=='PROVIDER_TIMEOUT' else 'ACCESS_WALK_UNAVAILABLE'
        after,_,_,fp=arrivals.owned(user_id,search_id,candidate_id);latest=place(user_id,origin_ref)
        arrivals.checked_mapping(entry.mapping,first,arrivals.now())
        if fp!=snapshot or cache.mapping_identity(entry.mapping)!=identity or latest['latitude']!=origin['latitude'] or latest['longitude']!=origin['longitude']:
            raise AuthError(409,'VERSION_CONFLICT','경로 또는 출발 장소가 변경됐어요.')
        if time.monotonic()>deadline:return None,'ACCESS_WALK_TIME_LIMIT'
        fetched=arrivals.now();expiry=min(row['expires_at'],after['expires_at'],mapping.valid_until,entry.expires_at,fetched+timedelta(seconds=300))
        if seconds is not None and (type(seconds) is not int or not 1<=seconds<=86400):seconds=None
        value={'seconds':seconds,'fetched_at':fetched,'expires_at':expiry,'origin_ref':origin_ref,'identity':identity,'reason':reason}
        entry.access_walk=value
        return (value,None) if seconds is not None else (None,reason)
    finally:entry.lock.release()
