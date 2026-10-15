"""Fresh routine departure queries; bounded memory binding, never rewrite a plan."""
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime,timezone
from threading import Lock
import json
from fastapi import BackgroundTasks,Request
from pydantic import BaseModel,ConfigDict,StrictInt,Field
from app.auth import security
from app.common.database import database
from app.common.errors import AuthError
from app.common.response import answer
from app.common.timeutil import iso
from app.journeys import service as journeys
from app.journeys.dto import SearchInput
from app.journeys.models import common_candidate
from app.places.service import parsed_id
from app.routines import repository,service as routines
from app.guidance import service as departure


class RefreshInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    expected_version:StrictInt=Field(ge=1)


@dataclass(frozen=True)
class Binding:
    user_id:object
    routine_id:object
    version:int
    plan_id:object
    signature:str
    expires_at:datetime
    place_refs:tuple


_bindings=OrderedDict()
_guard=Lock()


def signature(candidate):
    route=common_candidate(candidate)
    return json.dumps([(leg['type'],leg['walking_role'],leg['stops'],leg['vehicles'])
        for leg in route['ordered_legs']],ensure_ascii=False,separators=(',',':'))


def current(user_id,routine_id,version):
    with database() as connection:
        row=repository.find_routine(connection,routine_id,user_id)
        if row is None:routines.missing_routine()
        if row['version']!=version or row['status']!='active':
            raise AuthError(409,'VERSION_CONFLICT','루틴이 바뀌었거나 복구가 필요해요. 루틴을 다시 확인해주세요.')
        plan=repository.find_plan(connection,row['journey_plan_id'])
        if plan is None or plan['user_id']!=user_id:routines.missing_routine()
        places=[repository.find_owned_place(connection,row[key],user_id)
            for key in ('origin_place_id','destination_place_id')]
        if any(place is None for place in places):routines.missing_place()
    return row,plan,places


def put(search_id,binding):
    with _guard:
        for key in list(_bindings):
            if _bindings[key].expires_at<=datetime.now(timezone.utc):del _bindings[key]
        previous=_bindings.get(str(search_id))
        if previous is not None and previous!=binding:raise AuthError(409,'VERSION_CONFLICT','검색 연결이 변경됐어요.')
        _bindings[str(search_id)]=binding;_bindings.move_to_end(str(search_id))
        while len(_bindings)>32:_bindings.popitem(last=False)


def checked(user_id,routine_id,search_id,version,*,with_row=False):
    with _guard:
        binding=_bindings.get(str(search_id))
    if binding is None or binding.user_id!=user_id or binding.routine_id!=routine_id or binding.expires_at<=datetime.now(timezone.utc):journeys.missing()
    if binding.version!=version:raise AuthError(409,'VERSION_CONFLICT','루틴 버전이 변경됐어요.')
    row,plan,places=current(user_id,routine_id,version)
    if row['journey_plan_id']!=binding.plan_id or signature(plan['candidate'])!=binding.signature:
        raise AuthError(409,'VERSION_CONFLICT','루틴 경로가 변경됐어요.')
    if tuple((str(p['id']),p['location_version']) for p in places)!=binding.place_refs:
        raise AuthError(409,'VERSION_CONFLICT','루틴 장소가 변경됐어요.')
    return (binding,row) if with_row else binding


def refresh(request:Request,routine_id,body,background:BackgroundTasks):
    routine_id=parsed_id(routine_id)
    with database() as connection:user_id=security.authenticated(connection,request,True)
    row,plan,places=current(user_id,routine_id,body.expected_version)
    query=SearchInput.model_validate({'origin':{'type':'saved_place','place_id':str(places[0]['id']),'location_version':places[0]['location_version']},
        'destination':{'type':'saved_place','place_id':str(places[1]['id']),'location_version':places[1]['location_version']},
        'timing':{'mode':'depart_now','timezone':'Asia/Seoul'}})
    outcome=journeys.search(request,query,context={'routine_id':str(routine_id),'version':body.expected_version})
    replay=outcome[0]=='replay'
    data=json.loads(outcome[1].body)['data'] if replay else outcome[1]
    search_id=parsed_id(data['search_id'])
    # If revalidation rejects admission, its unused queued lease expires safely.
    latest,latest_plan,latest_places=current(user_id,routine_id,body.expected_version)
    if latest['journey_plan_id']!=row['journey_plan_id'] or signature(latest_plan['candidate'])!=signature(plan['candidate']) or [(p['id'],p['location_version']) for p in places]!=[(p['id'],p['location_version']) for p in latest_places]:
        raise AuthError(409,'VERSION_CONFLICT','루틴 또는 장소가 변경됐어요.')
    with database() as connection:
        search=repository.find_journey_search(connection,search_id,user_id)
        journeys.check_refs(connection,user_id,search['place_refs'])
    binding=Binding(user_id,routine_id,row['version'],row['journey_plan_id'],signature(plan['candidate']),search['expires_at'],tuple((str(p['id']),p['location_version']) for p in places))
    if replay:checked(user_id,routine_id,search_id,body.expected_version)
    else:
        put(search_id,binding)
        background.add_task(journeys.execute,*outcome[2])
    return answer(request,{**data,'routine_id':str(routine_id),'routine_version':row['version']},202)


def result(request:Request,routine_id,search_id,expected_version):
    routine_id=parsed_id(routine_id);search_id=parsed_id(search_id)
    with database() as connection:user_id=security.authenticated(connection,request)
    binding,routine_row=checked(user_id,routine_id,search_id,expected_version,with_row=True)
    row=journeys.owned(request,str(search_id))
    if tuple((r['place_id'],r['location_version']) for r in row['place_refs'])!=binding.place_refs:
        raise AuthError(409,'VERSION_CONFLICT','검색 장소가 변경됐어요.')
    if not isinstance(row['candidates'],list) or len(row['candidates'])>20:
        raise AuthError(502,'PROVIDER_RESPONSE_INVALID','경로 후보를 확인할 수 없어요.')
    data={'model_version':'routine.departure.v1','routine_id':str(routine_id),'routine_version':binding.version,
        'search_id':str(search_id),'status':'searching','candidate_id':None,'departure':None,'expires_at':iso(row['expires_at'])}
    lease=None
    try:
        if row['status']=='failed':
            error=row['error'] or {};raise AuthError(503,error.get('code','PROVIDER_UNAVAILABLE'),'최신 경로를 확인하지 못했어요. 다시 확인해주세요.')
        if row['status']=='succeeded':
            candidates=[common_candidate(c) for c in row['candidates']]
            matches=[c for c in candidates if signature(c)==binding.signature]
            data['status']='no_routes' if not candidates else 'route_changed' if not matches else 'ambiguous_route' if len(matches)>1 else 'ready'
            if data['status']=='ready':
                candidate=matches[0];data['candidate_id']=candidate['candidate_id']
                from app.guidance import selection
                lease=selection.begin(binding)
                value=departure.first_departure(user_id,search_id,parsed_id(candidate['candidate_id']),include_connections=True,access_origin_ref=binding.place_refs[0],destination_ref=binding.place_refs[1],selector=lease.choose,reported_departure=lease.reported)
                from app.guidance import target
                profile=departure.settings(user_id)
                if profile['version']!=value.profile_version or (value.applied_duration_factor is not None and profile['factor']!=value.applied_duration_factor) or profile['buffer']!=value.buffer_seconds:
                    raise AuthError(409,'VERSION_CONFLICT','개인 설정이 변경됐어요.')
                value.target_evaluation=target.evaluate(candidate,value,routine_row['target_arrival_local_time'],profile,departure.arrivals.now())
                if departure.settings(user_id)!=profile:raise AuthError(409,'VERSION_CONFLICT','개인 설정이 변경됐어요.')
                data['departure']=value.model_dump(mode='json')
        checked(user_id,routine_id,search_id,expected_version)
        latest=journeys.owned(request,str(search_id))
        if latest['candidates']!=row['candidates'] or latest['status']!=row['status'] or latest['place_refs']!=row['place_refs']:
            raise AuthError(409,'VERSION_CONFLICT','최신 경로가 변경됐어요.')
        if data['departure'] is not None:
            lease.commit(value)
            from app.guidance import issued
            data['departure']['guidance_id']=issued.publish(binding,candidate,value,profile)
            if data['departure']['guidance_id'] is not None:data['departure']['guidance_id']=str(data['departure']['guidance_id'])
        data['expires_at']=iso(min(row['expires_at'],latest['expires_at'],binding.expires_at))
        response=answer(request,data)
        if data['status']=='searching':response.headers['Retry-After']='2'
        return response
    finally:
        if lease is not None:lease.close()
