"""Manual self reports are not verified movement or personal learning samples."""
import hashlib,json,math,re
from datetime import datetime,timezone,timedelta
from uuid import uuid4
from app.auth import security
from app.common.database import database
from app.common.errors import AuthError
from app.common.response import answer
from app.common.timeutil import iso
from app.places.service import parsed_id
from app.guidance import issued,routine
from app.arrivals import cache
from app.trips import repository as repo
from app.trips.progress import state as progress_state

def missing():raise AuthError(404,'RESOURCE_NOT_FOUND','이동 기록이나 안내를 찾을 수 없어요.')
def conflict():raise AuthError(409,'VERSION_CONFLICT','안내나 개인 설정이 변경됐어요. 다시 확인해주세요.')
def order():raise AuthError(409,'INVALID_EVENT_ORDER','이 이동의 기록 순서를 확인해주세요.')
def authenticate(request,kind=None):
    with database() as c:
        owner=security.authenticated(c,request,kind is not None)
        if kind:
            _,secret,_=security.settings()
            security.increment(c,security.bucket(c,'trip-'+kind,str(owner),60,10 if kind=='create' else 30,secret))
    return owner

def event_data(row):
    return {**{k:str(row[k]) for k in ('trip_id','client_event_id','leg_id')},
        'event_id':str(row['id']),'type':row['type'],'source':row['source'],
        'occurred_at':row['occurred_at'].astimezone(timezone.utc).isoformat(),
        'received_at':row['received_at'].isoformat(),
        'input_delay_seconds':math.floor((row['received_at']-row['occurred_at']).total_seconds()),
        'excluded':row['excluded'],'version':row['version']}

def trip_data(c,row):
    values=repo.events(c,row['id'])
    legs=row['snapshot']['candidate']['ordered_legs']
    first=next(i for i,leg in enumerate(legs) if leg['type'] in ('BUS','SUBWAY'))
    access=legs[first-1]['leg_id'] if first else legs[first]['leg_id']
    return {'trip_id':str(row['id']),'guidance_id':str(row['guidance_id']),
        'routine_id':str(row['routine_id']) if row['routine_id'] else None,
        'measurement_mode':row['measurement_mode'],'status':row['status'],'version':row['version'],
        'created_at':iso(row['created_at']),'expires_at':iso(row['expires_at']),
        'progress':progress_state(row['snapshot']['candidate'],values),
        **{field:next((event_data(e) for e in values if e['type']==kind and str(e['leg_id'])==lid),None)
           for field,kind,lid in [('departure_event','departed',legs[0]['leg_id']),('approach_event','approach_arrived',access),('boarding_event','boarded',legs[first]['leg_id'])]}}

def create(request,body):
    owner=authenticate(request,'create')
    key=request.headers.get('idempotency-key')
    if key is not None and re.fullmatch(r'[A-Za-z0-9_-]{1,128}',key) is None:
        raise AuthError(422,'VALIDATION_ERROR','재시도 키를 확인해주세요.')
    digest=hashlib.sha256(json.dumps(body.model_dump(mode='json'),sort_keys=True).encode()).hexdigest()
    with database() as c:
        repo.lock_owner(c,owner);repo.clean(c,owner)
        previous_key=repo.retry_key(c,owner,key) if key is not None else None
        if previous_key:
            if previous_key['body_hash']!=digest:raise AuthError(409,'IDEMPOTENCY_CONFLICT','같은 키의 이동 요청이 달라요.')
            trip=repo.owned(c,owner,previous_key['trip_id'])
            if trip is None:missing()
            return answer(request,trip_data(c,trip),200)
        previous=repo.same_guidance(c,owner,body.guidance_id)
        if previous:
            if previous['measurement_mode']!=body.measurement_mode:raise AuthError(409,'IDEMPOTENCY_CONFLICT','같은 안내의 측정 방식이 달라요.')
            if key is not None:repo.save_key(c,owner,key,digest,previous['id'])
            return answer(request,trip_data(c,previous),200)
        value=issued.owned(owner,body.guidance_id);binding=value['binding'];d=value['departure'];route=value['route']
        if repo.active(c,owner):raise AuthError(409,'ACTIVE_TRIP_EXISTS','진행 중인 이동을 먼저 확인하거나 취소해주세요.')
        row,places=repo.source(c,owner,binding,parsed_id(d['search_id']))
        if row is None or any(p is None for p in places):missing()
        if row['routine_status']!='active' or row['routine_version']!=binding.version or row['journey_plan_id']!=binding.plan_id or routine.signature(row['plan_candidate'])!=binding.signature:conflict()
        if tuple((str(p['id']),p['location_version']) for p in places)!=binding.place_refs or tuple((r['place_id'],r['location_version']) for r in row['place_refs'])!=binding.place_refs:conflict()
        candidate=next((item for item in row['candidates'] if item['candidate_id']==d['candidate_id']),None)
        if row['search_status']!='succeeded' or row['search_expires']<=datetime.now(timezone.utc) or candidate is None:missing()
        if cache.fingerprint(candidate)!=cache.fingerprint(route) or row['profile_version']!=d['profile_version'] or row['walking_duration_factor']!=d['applied_duration_factor'] or row['first_boarding_buffer_seconds']!=d['buffer_seconds'] or row['transfer_buffer_seconds']!=value['profile']['transfer_buffer']:conflict()
        if value['expires_at']<datetime.now(timezone.utc):missing()
        if datetime.fromisoformat(d['vehicle_arrival_at'].replace('Z','+00:00'))-datetime.now(timezone.utc)<timedelta(seconds=d['approach_seconds']):missing()
        d['guidance_id']=str(body.guidance_id)
        snapshot={'departure':d,'candidate':route,'routine_version':binding.version,'place_refs':list(binding.place_refs)}
        trip=repo.insert(c,owner,body.guidance_id,uuid4(),binding.routine_id,snapshot,body.measurement_mode)
        if key is not None:repo.save_key(c,owner,key,digest,trip['id'])
        return answer(request,trip_data(c,trip),201)

def detail(request,trip_id):
    owner=authenticate(request)
    with database() as c:
        row=repo.owned(c,owner,parsed_id(trip_id))
        if row is None:missing()
        return answer(request,{'trip':trip_data(c,row),'guidance':row['snapshot'],
            'events':[event_data(e) for e in repo.events(c,row['id'])],'outcome':None if row['status']=='active' else 'cancelled'})

def listed(request,limit,cursor,routine_id,status):
    owner=authenticate(request)
    with database() as c:
        anchor=repo.owned(c,owner,parsed_id(cursor)) if cursor else None
        if cursor and anchor is None:missing()
        rows=repo.listed(c,owner,parsed_id(routine_id) if routine_id else None,status,anchor,limit)
        return answer(request,{'items':[trip_data(c,r) for r in rows[:limit]],'next_cursor':str(rows[limit-1]['id']) if len(rows)>limit else None})

def add_event(request,trip_id,body):
    owner=authenticate(request,'event')
    canonical=body.model_dump(mode='json');canonical['occurred_at']=body.occurred_at.astimezone(timezone.utc).isoformat()
    digest=hashlib.sha256(json.dumps(canonical,sort_keys=True).encode()).hexdigest()
    with database() as c:
        repo.lock_owner(c,owner);repo.clean(c,owner)
        row=repo.owned(c,owner,parsed_id(trip_id),True)
        if row is None:missing()
        previous=repo.event(c,row['id'],body.client_event_id)
        if previous:
            if previous['body_hash']!=digest:raise AuthError(409,'IDEMPOTENCY_CONFLICT','같은 출발 확인의 내용이 달라요.')
            return answer(request,event_data(previous),200)
        events=repo.events(c,row['id'])
        if row['status']!='active':order()
        progress=progress_state(row['snapshot']['candidate'],events)
        if body.type not in progress['actions']:order()
        now=datetime.now(timezone.utc);snapshot=row['snapshot']
        calculated=datetime.fromisoformat(snapshot['departure']['calculated_at'].replace('Z','+00:00'))
        expected=progress['actions'][body.type]
        lower=max([calculated]+[e['occurred_at'] for e in events])
        if str(body.leg_id)!=expected or not lower<=body.occurred_at<=now:
            raise AuthError(422,'VALIDATION_ERROR','이동 구간과 발생 시각을 확인해주세요.')
        event=repo.add_event(c,row['id'],uuid4(),body,digest,now)
        return answer(request,event_data(event),201)

def cancel(request,trip_id,body):
    owner=authenticate(request,'event')
    with database() as c:
        repo.lock_owner(c,owner);repo.clean(c,owner)
        row=repo.owned(c,owner,parsed_id(trip_id),True)
        if row is None:missing()
        if row['version']!=body.expected_version:conflict()
        if row['status']=='active':repo.cancel(c,row['id'])
        return answer(request,trip_data(c,repo.owned(c,owner,row['id'])))
