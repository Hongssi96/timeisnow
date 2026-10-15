"""Current confirmed point only; elapsed departure time never proves progress."""
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime,timedelta,timezone
from threading import Lock
import json
from app.common.database import database
from app.common.errors import AuthError
from app.common.response import answer
from app.common.timeutil import iso
from app.journeys import service as journeys
from app.journeys.dto import SearchInput
from app.journeys.models import common_candidate
from app.places.service import parsed_id
from app.trips import service as trips,repository as repo
from app.guidance import routine,service as departure,target

_bindings=OrderedDict()
_guard=Lock()

@dataclass(frozen=True)
class Binding:
    owner:object
    trip_id:object
    version:int
    event_id:object
    routine_id:object
    routine_version:int
    plan_id:object
    signature:str
    place_refs:tuple
    profile:dict
    expires_at:datetime

def suffix_signature(candidate):
    route=common_candidate(candidate)
    first=next(leg['sequence'] for leg in route['ordered_legs'] if leg['type']!='WALKING')
    return json.dumps([(leg['type'],leg['walking_role'],leg['stops'],leg['vehicles'])
        for leg in route['ordered_legs'][first:]],ensure_ascii=False,separators=(',',':'))

def source(owner,trip_id,version):
    with database() as c:
        row=repo.owned(c,owner,trip_id)
        if row is None:trips.missing()
        events=repo.events(c,trip_id)
    if any(e['type'] in ('approach_arrived','boarded') for e in events):
        raise AuthError(409,'INVALID_EVENT_ORDER','접근 완료나 탑승을 기록했어요. 첫 탑승 전 접근 안내를 종료해주세요.')
    if row['version']!=version or row['status']!='active' or len(events)!=1 or events[0]['type']!='departed' or events[0]['source']!='manual' or events[0]['excluded']:
        raise AuthError(409,'VERSION_CONFLICT','유효한 출발 확인과 진행 중인 이동이 필요해요.')
    snap=row['snapshot']
    r,plan,places=routine.current(owner,row['routine_id'],snap['routine_version'])
    refs=tuple((str(p['id']),p['location_version']) for p in places)
    if tuple(tuple(x) for x in snap['place_refs'])!=refs or routine.signature(plan['candidate'])!=routine.signature(snap['candidate']):
        raise AuthError(409,'VERSION_CONFLICT','이동의 장소나 경로가 변경됐어요.')
    return row,events[0],r,plan,places,refs

def checked(owner,trip_id,search_id,version):
    with _guard:b=_bindings.get(str(search_id))
    if b is None or b.owner!=owner or b.trip_id!=trip_id or b.expires_at<=departure.arrivals.now():journeys.missing()
    row,event,r,plan,places,refs=source(owner,trip_id,version)
    if b.version!=version or b.event_id!=event['id'] or b.routine_id!=r['id'] or b.routine_version!=r['version'] or b.plan_id!=r['journey_plan_id'] or b.signature!=routine.signature(plan['candidate']) or b.place_refs!=refs or departure.settings(owner)!=b.profile:
        raise AuthError(409,'VERSION_CONFLICT','이동이나 개인 설정이 변경됐어요. 현재 위치를 다시 확인해주세요.')
    return b,r,row

def refresh(request,trip_id,body,background):
    owner=trips.authenticate(request,'create');trip_id=parsed_id(trip_id)
    row,event,r,plan,places,refs=source(owner,trip_id,body.expected_version)
    profile=departure.settings(owner)
    query=SearchInput.model_validate({'origin':body.origin.model_dump(mode='json'),
        'destination':{'type':'saved_place','place_id':str(places[1]['id']),'location_version':places[1]['location_version']},
        'timing':{'mode':'depart_now','timezone':'Asia/Seoul'}})
    outcome=journeys.search(request,query,context={'trip_id':str(trip_id),'version':body.expected_version,'stage':body.stage})
    replay=outcome[0]=='replay'
    data=json.loads(outcome[1].body)['data'] if replay else outcome[1]
    sid=parsed_id(data['search_id'])
    if replay:b,_,_=checked(owner,trip_id,sid,body.expected_version)
    else:
        latest=source(owner,trip_id,body.expected_version)
        if latest[1]['id']!=event['id'] or latest[2]['journey_plan_id']!=r['journey_plan_id'] or latest[5]!=refs or departure.settings(owner)!=profile:
            raise AuthError(409,'VERSION_CONFLICT','이동이나 개인 설정이 변경됐어요.')
        search=journeys.owned(request,str(sid))
        b=Binding(owner,trip_id,row['version'],event['id'],r['id'],r['version'],r['journey_plan_id'],routine.signature(plan['candidate']),refs,profile,
            min(search['created_at']+timedelta(seconds=120),search['expires_at']))
        if b.expires_at<=departure.arrivals.now():journeys.missing()
        with _guard:
            for key in list(_bindings):
                if _bindings[key].expires_at<=departure.arrivals.now():del _bindings[key]
            _bindings[str(sid)]=b
            while len(_bindings)>32:_bindings.popitem(last=False)
        background.add_task(journeys.execute,*outcome[2])
    return answer(request,{**data,'trip_id':str(trip_id),'trip_version':b.version,'position_valid_until':iso(b.expires_at)},202)

def result(request,trip_id,search_id,version):
    owner=trips.authenticate(request);trip_id=parsed_id(trip_id);search_id=parsed_id(search_id)
    b,r,trip=checked(owner,trip_id,search_id,version)
    search=journeys.owned(request,str(search_id));at=departure.arrivals.now()
    data={'model_version':'trip.remaining.v1','trip_id':str(trip_id),'trip_version':version,'search_id':str(search_id),
        'candidate_id':None,'status':'searching','calculated_at':iso(at),'valid_until':iso(min(b.expires_at,search['expires_at'])),
        'valid_for_guidance':False,'remaining_approach_seconds':None,'buffer_seconds':b.profile['buffer'],
        'vehicle_arrival_at':None,'slack_seconds':None,'slack_status':'unknown','timing_basis':'none',
        'connection_status':'not_checked','transfers':[],'target_evaluation':None,'reasons':['CONFIRMED_POINT_ESTIMATE']}
    if search['status']=='failed':
        raise AuthError(503,(search['error'] or {}).get('code','PROVIDER_UNAVAILABLE'),'남은 경로를 확인하지 못했어요.')
    if search['status']=='succeeded':
        candidates=[common_candidate(c) for c in search['candidates']]
        matches=[c for c in candidates if suffix_signature(c)==suffix_signature(trip['snapshot']['candidate'])]
        data['status']='no_routes' if not candidates else 'route_changed' if not matches else 'ambiguous_route' if len(matches)>1 else 'ready'
        if data['status']=='ready':
            candidate=matches[0];data['candidate_id']=candidate['candidate_id']
            value=departure.first_departure(owner,search_id,parsed_id(candidate['candidate_id']),basis='now',include_connections=True)
            evaluation=target.evaluate(candidate,value,r['target_arrival_local_time'],b.profile,departure.arrivals.now())
            data.update(status=value.status,calculated_at=value.calculated_at.isoformat(),valid_until=iso(min(b.expires_at,value.valid_until)),
                valid_for_guidance=value.valid_for_guidance,reasons=list(dict.fromkeys(data['reasons']+value.reasons)))
            if value.valid_for_guidance:
                data.update(remaining_approach_seconds=value.approach_seconds,vehicle_arrival_at=value.vehicle_arrival_at.isoformat(),
                    slack_seconds=value.slack_seconds,slack_status=value.slack_status,timing_basis=value.timing_basis,
                    connection_status=value.connection_status,transfers=[x.model_dump(mode='json') for x in value.transfers],
                    target_evaluation=evaluation.model_dump(mode='json'))
    checked(owner,trip_id,search_id,version)
    latest=journeys.owned(request,str(search_id))
    if latest['candidates']!=search['candidates'] or latest['status']!=search['status'] or latest['place_refs']!=search['place_refs']:
        raise AuthError(409,'VERSION_CONFLICT','남은 경로가 변경됐어요.')
    if departure.arrivals.now()>=datetime.fromisoformat(data['valid_until']):
        journeys.missing()
    if data['vehicle_arrival_at'] and departure.arrivals.now()>=datetime.fromisoformat(data['vehicle_arrival_at']):
        data.update(status='stale',valid_for_guidance=False,remaining_approach_seconds=None,vehicle_arrival_at=None,
            slack_seconds=None,slack_status='unknown',timing_basis='none',connection_status='stale',transfers=[],target_evaluation=None)
    response=answer(request,data)
    if data['status']=='searching':response.headers['Retry-After']='2'
    return response
