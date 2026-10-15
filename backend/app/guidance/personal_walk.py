"""Explicit AI estimation from validated provider geometry; GET never calls AI."""
from datetime import timedelta
from uuid import UUID
import time
from pydantic import BaseModel,ConfigDict,Field,StrictInt
from app.auth import security
from app.common.database import database
from app.common.errors import AuthError
from app.common.response import answer
from app.arrivals import cache,service as arrivals
from app.guidance import access,routine,service,walk_provider
from app.guidance.dto import PersonalWalk
from app.walking import history_service,history_repository
from app.journeys.service import check_refs

SCOPE='provider_mapped_access'

class EstimateInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    expected_version: StrictInt=Field(ge=1)
    client_request_id: UUID


def read(user_id,entry,first,origin_ref,profile):
    """Only the server-attached revision and current verified origin may be used."""
    item=entry.personal_walk if entry else None
    if item is None or entry.mapping is None:return None
    if item['origin_ref']!=origin_ref or item['mapping_identity']!=cache.mapping_identity(entry.mapping):return None
    at=arrivals.now()
    if not item['fetched_at']<=at<item['expires_at']:return None
    with database() as connection:
        row=history_repository.summary(connection,user_id,item['estimate_id'])
        if row is None or row['scope']!=SCOPE or row['id']!=item['revision_id'] or row['profile_version']!=profile['version'] or row['expires_at']<=at:return None
        check_refs(connection,user_id,row['place_refs'])
    if float(row['applied_duration_factor'])!=profile['factor']:return None
    from app.guidance.route_walks import personalized
    if personalized(float(row['base_seconds']),profile['factor'])!=row['estimated_seconds']:return None
    return PersonalWalk(estimate_id=row['estimate_id'],revision_id=row['id'],base_seconds=float(row['base_seconds']),
        applied_duration_factor=float(row['applied_duration_factor']),estimated_seconds=row['estimated_seconds'],
        profile_version=row['profile_version'],source=row['source'],reused=item['reused'],expires_at=min(row['expires_at'],item['expires_at']))


def result(request,routine_id,search_id,body):
    rid=arrivals.parsed_id(routine_id);sid=arrivals.parsed_id(search_id)
    with database() as connection:user_id=security.authenticated(connection,request,True)
    binding=routine.checked(user_id,rid,sid,body.expected_version)
    from app.guidance import selection
    lease=selection.begin(binding)
    try:
        if lease.reported:raise AuthError(409,'VERSION_CONFLICT','출발 확인 후에는 새 도보 산정을 적용할 수 없어요.')
    finally:lease.close()
    from app.journeys import service as journeys
    from app.journeys.models import common_candidate
    row=journeys.owned(request,str(sid))
    payload={'model_version':'routine.walking.v1','routine_id':str(rid),'search_id':str(sid),'status':'needs_data','estimate':None,'reasons':[]}
    def missing(reason):
        payload['reasons']=[reason];return answer(request,payload)
    if row['status']!='succeeded':return missing('ROUTE_UNCONFIRMED')
    if not isinstance(row['candidates'],list) or len(row['candidates'])>20:raise AuthError(502,'PROVIDER_RESPONSE_INVALID','경로를 확인해주세요.')
    candidates=[common_candidate(c) for c in row['candidates']]
    matches=[c for c in candidates if routine.signature(c)==binding.signature]
    if len(matches)!=1:return missing('ROUTE_UNCONFIRMED')
    route=matches[0];cid=arrivals.parsed_id(route['candidate_id'])
    before,_,first,fp=arrivals.owned(user_id,sid,cid)
    entry=cache.lookup(user_id,sid,cid,fp,arrivals.now())
    if first['type']!='BUS' or entry is None or entry.mapping is None or entry.boarding_endpoint is None:return missing('ACCESS_MAPPING_REQUIRED')
    if not entry.personal_walk_lock.acquire(blocking=False):raise AuthError(429,'RATE_LIMITED','개인 도보 산정이 진행 중이에요.',{'Retry-After':'2'})
    try:
        profile=service.settings(user_id);mapping=arrivals.checked_mapping(entry.mapping,first,arrivals.now())
        identity=cache.mapping_identity(mapping);origin_ref=binding.place_refs[0]
        origin=access.place(user_id,origin_ref)
        def validate():
            current=routine.checked(user_id,rid,sid,body.expected_version)
            latest,_,_,snapshot=arrivals.owned(user_id,sid,cid)
            point=access.place(user_id,origin_ref)
            if snapshot!=fp or current!=binding or service.settings(user_id)!=profile or any(point[k]!=origin[k] for k in ('latitude','longitude')):
                raise AuthError(409,'VERSION_CONFLICT','루틴·장소·개인 설정이 변경됐어요.')
            arrivals.checked_mapping(entry.mapping,first,arrivals.now())
            if cache.mapping_identity(entry.mapping)!=identity or entry.boarding_endpoint.get('mapping_identity')!=identity:
                raise AuthError(409,'VERSION_CONFLICT','승차 근거가 변경됐어요.')
            lease=selection.begin(binding)
            try:
                if lease.reported:raise AuthError(409,'VERSION_CONFLICT','이미 출발 확인한 안내예요.')
            finally:lease.close()
        validate()
        prepared=entry.personal_walk_request
        now=arrivals.now()
        if prepared and prepared['mapping_identity']==identity and prepared['origin_ref']==origin_ref and prepared['context']['valid_until']>now:
            evidence=prepared['evidence'];verified=prepared['context']['verified_at'];expiry=prepared['context']['valid_until'];fetched=prepared['fetched_at']
        else:
            arrivals.reserve_refresh(user_id)
            evidence=walk_provider.fetch((origin['longitude'],origin['latitude']),entry.boarding_endpoint['point'],time.monotonic()+5,details=True)
            validate()
            if evidence is None:return missing('ACCESS_WALK_UNAVAILABLE')
            fetched=arrivals.now()
            # The enclosing search's DB timestamp is a conservative lower bound.
            # Receipt time stays separate; neither clock can extend the search TTL.
            verified=before['created_at']
            expiry=min(before['expires_at'],entry.expires_at,mapping.valid_until,verified+timedelta(seconds=300))
        if not isinstance(evidence,dict) or type(evidence.get('seconds')) is not int or not 1<=evidence['seconds']<=86400 or not isinstance(evidence.get('path_fingerprint'),str) or len(evidence['path_fingerprint'])!=64:
            raise AuthError(502,'PROVIDER_RESPONSE_INVALID','검증된 도보 경로를 확인해주세요.')
        data={'request_id':'routine.walking.'+str(body.client_request_id),'policy_version':'walk-policy.v1',
            'profile':{'version':profile['version'],'validated_duration_factor':profile['factor'],'valid_factor_range':[.5,2.0],'fallback_speed_mps':None},
            'candidates':[{'candidate_id':'access','origin_ref':'saved_origin','destination_ref':'boarding_stop',
                'direction':'origin_to_boarding','scope':SCOPE,'required_scope':SCOPE,'is_walkable_route':True,
                'distance_meters':None,'provider_duration_seconds':float(evidence['seconds']),
                'provider_duration_includes_personalization':False,'evidence_ids':['validated_walking_route'],'missing_segments':[]}]}
        context={'place_refs':[{'place_id':origin_ref[0],'location_version':origin_ref[1]}],'verified_at':verified,'valid_until':expiry}
        # Real identities remain server-side, outside the model's input.
        physical=history_service.fingerprint({'path':evidence['path_fingerprint'],'mapping':[mapping.provider,mapping.station_id,mapping.route_id,mapping.sta_order,mapping.route_dest_id]})
        sources=[{'candidate_id':'access','provider':'kakao-walking','provider_path_ref':physical,'path_version':'geometry.v1',
            'origin_entrance_ref':'not_applicable','destination_entrance_ref':'not_applicable','condition_version':'walk-validation.v2'}]
        if prepared and prepared['data']['request_id']==data['request_id'] and prepared['data']!=data:
            raise AuthError(409,'IDEMPOTENCY_CONFLICT','변경된 설정에는 새 산정 요청을 사용해주세요.')
        entry.personal_walk_request={'data':data,'context':context,'evidence':evidence,'origin_ref':origin_ref,'mapping_identity':identity,'fetched_at':fetched}
        stored=history_service.estimate_and_store(user_id,data,context=context,cache_sources=sources,validate_context=validate)
        validate()
        if len(stored['estimates'])!=1:return missing('AI_ESTIMATE_UNCONFIRMED')
        link=stored['estimates'][0]
        entry.personal_walk={'estimate_id':arrivals.parsed_id(link['estimate_id']),'revision_id':arrivals.parsed_id(link['revision_id']),
            'origin_ref':origin_ref,'mapping_identity':identity,'fetched_at':fetched,'expires_at':expiry,'reused':link['reused']}
        value=read(user_id,entry,first,origin_ref,profile)
        if value is None:return missing('AI_ESTIMATE_UNCONFIRMED')
        payload.update(status='validated',estimate=value.model_dump(mode='json'))
        return answer(request,payload)
    finally:entry.personal_walk_lock.release()
