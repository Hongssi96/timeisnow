"""Owned first boarding evidence; unverified public mappings never fetch."""
from datetime import datetime,timedelta,timezone
from uuid import uuid5,NAMESPACE_URL
from pydantic import ValidationError
from app.auth import security
from app.common.database import database
from app.common.errors import AuthError
from app.common.response import answer
from app.journeys.models import common_candidate
from app.journeys.service import check_refs,missing
from app.places.service import parsed_id
from app.arrivals import repository,provider,cache,mapping as public_mapping
from app.arrivals.dto import Mapping,Evidence,Arrival


def now():return datetime.now(timezone.utc)

def owned(user_id,search_id,candidate_id):
    with database() as connection:
        row=repository.search(connection,user_id,search_id)
        if not row or row['status']!='succeeded' or row['expires_at']<=now():missing()
        check_refs(connection,user_id,row['place_refs'])
    values=row['candidates']
    if not isinstance(values,list) or len(values)>20:provider.invalid()
    candidates=[common_candidate(value) for value in values]
    candidate=next((item for item in candidates if item['candidate_id']==str(candidate_id)),None)
    if candidate is None:missing()
    first=next(leg for leg in candidate['ordered_legs'] if leg['type']!='WALKING')
    fingerprint=cache.fingerprint(candidate)
    return row,candidate,first,fingerprint


def checked_mapping(value,first,at):
    try:
        mapping=Mapping.model_validate(value.model_dump() if isinstance(value,Mapping) else value)
        if mapping.first_leg_id!=parsed_id(first['leg_id']) or mapping.verified_at.tzinfo is None or mapping.valid_until.tzinfo is None or mapping.verified_at>at or mapping.valid_until<=mapping.verified_at:
            raise ValueError()
        if mapping.valid_until<=at:missing()
        return mapping
    except (ValidationError,ValueError,TypeError):raise AuthError(422,'VALIDATION_ERROR','검증된 첫 탑승 매핑을 확인해주세요.') from None


def normalize(mapping,values,received_at,at,search_id,candidate_id,search_expires,generated_at=None):
    expires=min(received_at+timedelta(seconds=120),mapping.valid_until,search_expires)
    source='unknown';reasons=[];generation=None
    if isinstance(generated_at,datetime) and generated_at.tzinfo is not None:
        generation=generated_at;expires=min(expires,generation+timedelta(seconds=120))
        source='clock_mismatch' if generation>at or generation>received_at else 'stale' if at-generation>timedelta(seconds=120) else 'fresh'
    if at<received_at:source='clock_mismatch'
    if at>expires:status='expired';reasons=['ARRIVAL_EXPIRED']
    elif source!='fresh':status='insufficient_data';reasons=['GENERATION_TIME_UNCONFIRMED' if source=='unknown' else 'SOURCE_TIME_UNCONFIRMED']
    else:status='fresh'
    candidates=[]
    for vehicle,seconds in values or []:
        predicted=generation+timedelta(seconds=seconds) if source=='fresh' else None
        if predicted is not None and predicted<=at:continue
        identity=f'{search_id}:{candidate_id}:{mapping.provider}:{mapping.station_id}:{mapping.route_id}:{mapping.sta_order}:{mapping.route_dest_id}:{mapping.mapping_version}:{vehicle}'
        candidates.append(Arrival(candidate_id=uuid5(NAMESPACE_URL,identity),provider_prediction_seconds=seconds,predicted_arrival_at=predicted))
    candidates.sort(key=lambda item:(item.provider_prediction_seconds,str(item.candidate_id)))
    if values==[] and status!='expired':status='no_arrivals'
    elif not candidates and status=='fresh':status='insufficient_data';reasons=['PREDICTION_UNCONFIRMED']
    elif values is None and status!='expired':status='insufficient_data';reasons=list(dict.fromkeys(reasons+['PREDICTION_UNCONFIRMED']))
    return Evidence(search_id=search_id,candidate_id=candidate_id,first_leg_id=mapping.first_leg_id,status=status,source_status=source,
        received_at=received_at,generated_at=generation,expires_at=expires,valid_for_guidance=status=='fresh' and bool(candidates),reasons=reasons,candidates=candidates)


def reserve_refresh(user_id):
    with database() as connection:
        _,secret,_=security.settings()
        security.increment(connection,security.bucket(connection,'first-arrivals',str(user_id),60,10,secret))


def unmapped(row,first,search_id,candidate_id):
    return Evidence(search_id=search_id,candidate_id=candidate_id,first_leg_id=first['leg_id'],
        status='mapping_required' if first['type']=='BUS' else 'unsupported',expires_at=row['expires_at'],
        reasons=['PUBLIC_MAPPING_UNCONFIRMED' if first['type']=='BUS' else 'PROVIDER_UNSUPPORTED'])


def first_arrivals(user_id,search_id,candidate_id,*,verified_mapping=None):
    user_id=parsed_id(str(user_id));search_id=parsed_id(str(search_id));candidate_id=parsed_id(str(candidate_id))
    row,candidate,first,snapshot=owned(user_id,search_id,candidate_id)
    if verified_mapping is None:
        entry=cache.lookup(user_id,search_id,candidate_id,snapshot,now()) if first['type']=='BUS' else None
        if entry is None: return unmapped(row,first,search_id,candidate_id)
        if not entry.lock.acquire(blocking=False):
            raise AuthError(429,'RATE_LIMITED','도착 정보 조회를 기다려주세요.',{'Retry-After':'2'})
        try:
            current,_,current_first,current_snapshot=owned(user_id,search_id,candidate_id)
            if current_snapshot!=snapshot: raise AuthError(409,'VERSION_CONFLICT','경로가 변경됐어요. 다시 확인해주세요.')
            if entry.evidence is not None and entry.attempted_at is not None and now()-entry.attempted_at<timedelta(seconds=60) and now()<=entry.evidence.expires_at:
                cached=entry.evidence.model_copy(deep=True)
                cached.expires_at=min(cached.expires_at,current['expires_at'],entry.expires_at)
                return cached
            reserve_refresh(user_id)
            value=entry.mapping or public_mapping.resolve(entry.context,min(entry.expires_at,current['expires_at']))
            if value is None:
                updated,_,updated_first,updated_snapshot=owned(user_id,search_id,candidate_id)
                if updated_snapshot!=snapshot: raise AuthError(409,'VERSION_CONFLICT','경로가 변경됐어요. 다시 확인해주세요.')
                evidence=unmapped(updated,updated_first,search_id,candidate_id)
            else:
                _,_,updated_first,updated_snapshot=owned(user_id,search_id,candidate_id)
                if updated_snapshot!=snapshot: raise AuthError(409,'VERSION_CONFLICT','경로가 변경됐어요. 다시 확인해주세요.')
                checked_mapping(value,updated_first,now())
                evidence=first_arrivals(user_id,search_id,candidate_id,verified_mapping=value)
                entry.mapping=value
            entry.evidence=evidence.model_copy(deep=True);entry.attempted_at=evidence.received_at or now()
            return evidence
        finally: entry.lock.release()
    mapping=checked_mapping(verified_mapping,first,now())
    if first['type']!='BUS':
        return Evidence(search_id=search_id,candidate_id=candidate_id,first_leg_id=first['leg_id'],status='unsupported',expires_at=min(row['expires_at'],mapping.valid_until),reasons=['PROVIDER_UNSUPPORTED'])
    values=provider.fetch(mapping);received=now()
    current,_,new_first,new_snapshot=owned(user_id,search_id,candidate_id)
    checked_mapping(mapping,new_first,now())
    if new_snapshot!=snapshot:raise AuthError(409,'VERSION_CONFLICT','경로가 변경됐어요. 다시 확인해주세요.')
    # GBIS queryTime is request time, not a verified generation timestamp.
    return normalize(mapping,values,received,now(),search_id,candidate_id,current['expires_at'])


def result(request,search_id,candidate_id):
    with database() as connection:user_id=security.authenticated(connection,request)
    evidence=first_arrivals(user_id,search_id,candidate_id)
    return answer(request,evidence.model_dump(mode='json'))
