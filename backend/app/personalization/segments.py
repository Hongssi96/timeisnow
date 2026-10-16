"""Empirical manual durations; no provider baseline, shared factor or inferred walks."""
import hashlib,json,math,unicodedata
from datetime import datetime,timezone,timedelta
from statistics import median
from uuid import UUID,uuid4
from typing import Literal
from fastapi import APIRouter,Request
from pydantic import BaseModel,ConfigDict,Field,StrictInt,StrictBool,AwareDatetime,field_validator
from app.common.database import database
from app.common.response import answer
from app.common.errors import AuthError
from app.places.service import parsed_id
from app.trips import service as trips,repository as trip_repo,record_repository as receipts
from app.trips.progress import state as progress
from app.guidance.routine import signature
from app.personalization import repository as learning,segments_repository as repo

class Start(BaseModel):
    model_config=ConfigDict(extra='forbid')
    client_request_id:UUID
    kind:Literal['station_internal','transfer']
    leg_id:UUID
    label:str=Field(min_length=1,max_length=60)
    occurred_at:AwareDatetime
    start_boundary_confirmed:Literal[True]
    @field_validator('occurred_at',mode='before')
    @classmethod
    def text_time(cls,v):
        if not isinstance(v,str):raise ValueError('ISO timestamp required')
        return v
    @field_validator('start_boundary_confirmed',mode='before')
    @classmethod
    def boolean(cls,v):
        if v is not True:raise ValueError('Confirmation required')
        return v
    @field_validator('label')
    @classmethod
    def label_text(cls,v):
        v=' '.join(unicodedata.normalize('NFKC',v).split())
        if not v or len(v)>60 or any(unicodedata.category(x).startswith('C') for x in v):raise ValueError('Invalid label')
        return v

class Mutation(BaseModel):
    model_config=ConfigDict(extra='forbid')
    expected_version:StrictInt=Field(ge=1)
    client_request_id:UUID

class Confirm(Mutation):
    same_scope:StrictBool
    condition:Literal['normal','running','detour','errand','late_input']
    apply_to_guidance:StrictBool

class Exclude(Mutation):excluded:StrictBool

def digest(value):return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,default=str).encode()).hexdigest()

def context(rid,version,route,refs,kind,leg):
    return digest([str(rid),version,signature(route),refs,kind,leg['sequence']])

def descriptors(trip):
    if trip['routine_id'] is None:return []
    s=trip['snapshot'];route=s['candidate'];vehicles=[l for l in route['ordered_legs'] if l['type']!='WALKING'];out=[]
    for i,leg in enumerate(vehicles):
        for kind in (['transfer'] if i else [])+(['station_internal'] if leg['type']=='SUBWAY' else []):
            key=context(trip['routine_id'],s['routine_version'],route,s['place_refs'],kind,leg)
            out.append({'kind':kind,'leg_id':leg['leg_id'],'context_key':key,
              'name':('역 입구 → '+leg['stops'][0]+' 승차 지점') if kind=='station_internal' else vehicles[i-1]['stops'][-1]+' 하차 지점 → '+leg['stops'][0]+' 승차 지점'})
    return out

def quality(row,generation):
    reasons=[];seconds=None
    if row['finish_received_at'] is None:return ['RECORDING'],None
    if row['anchor_at'] is None or row['ready_at'] is None:reasons.append('MISSING_WALK_EVENTS')
    else:
        seconds=(row['ready_at']-row['started_at']).total_seconds()
        if not row['anchor_at']<=row['started_at']<row['ready_at'] or not 1<=seconds<=7200:reasons.append('INVALID_WALK_INTERVAL')
        if row['anchor_excluded'] or row['ready_excluded']:reasons.append('EVENT_EXCLUDED')
        if not 0<=(row['ready_received_at']-row['ready_at']).total_seconds()<=60:reasons.append('INPUT_DELAY')
    if not 0<=(row['start_received_at']-row['started_at']).total_seconds()<=60:reasons.append('INPUT_DELAY')
    if row['generation']!=generation:reasons.append('BEFORE_RESET')
    if row['excluded']:reasons.append('MANUALLY_EXCLUDED')
    if not row['same_scope']:reasons.append('SCOPE_MISMATCH')
    if row['condition']!='normal':reasons.append(row['condition'].upper())
    return list(dict.fromkeys(reasons)),seconds

def pool(c,owner,key,label,generation):
    values=[]
    for row in repo.rows(c,owner,context=key):
        if row['label']!=label:continue
        reasons,seconds=quality(row,generation)
        if not reasons:values.append((seconds,row['expires_at'],str(row['id']),row['version']))
    values=values[:20]
    return {'sample_count':len(values),'estimate_seconds':math.ceil(median(v[0] for v in values)) if len(values)>=5 else None,
      'valid_until':min(v[1] for v in values).isoformat() if len(values)>=5 else None,
      'basis_key':digest([key,label,generation,values])}

def data(c,owner,row):
    generation=repo.generation(c,owner);reasons,seconds=quality(row,generation)
    stats=pool(c,owner,row['context_key'],row['label'],generation)
    ready=next((e for e in trip_repo.events(c,row['trip_id']) if e['type']=='approach_arrived' and str(e['leg_id'])==str(row['leg_id'])),None)
    # An approach event may be attached to the WALKING leg before the transit leg.
    if ready is None:
        trip=trip_repo.owned(c,owner,row['trip_id'])
        if trip:
            legs=trip['snapshot']['candidate']['ordered_legs'];i=next(i for i,l in enumerate(legs) if l['leg_id']==str(row['leg_id']))
            walk=legs[i-1]['leg_id'] if i else legs[i]['leg_id']
            ready=next((e for e in trip_repo.events(c,row['trip_id']) if e['type']=='approach_arrived' and str(e['leg_id'])==walk),None)
    return {'measurement_id':str(row['id']),'kind':row['kind'],'leg_id':str(row['leg_id']),'label':row['label'],
      'status':'recording' if reasons==['RECORDING'] else 'excluded' if reasons else 'valid','version':row['version'],
      'started_at':row['started_at'].isoformat(),'finished_at':row['ready_at'].isoformat() if row['ready_at'] else None,
      'observed_seconds':seconds,'predicted_seconds':row['predicted_seconds'],
      'predicted_arrival_at':row['predicted_arrival_at'].isoformat() if row['predicted_arrival_at'] else None,
      'reasons':reasons,'can_finish':row['finish_received_at'] is None and ready is not None,
      'apply_to_guidance':row['apply_to_guidance'],**stats}

def read(c,owner,trip):
    rows=repo.rows(c,owner,trip=trip['id']);events=trip_repo.events(c,trip['id']);p=progress(trip['snapshot']['candidate'],events)
    available=[]
    if trip['status']=='active' and 'approach_arrived' in p['actions']:
        for d in descriptors(trip):
            if d['leg_id']!=p['next_leg_id'] or any(r['kind']==d['kind'] and str(r['leg_id'])==d['leg_id'] for r in rows):continue
            labels=list(dict.fromkeys(r['label'] for r in repo.rows(c,owner,context=d['context_key'])))[:20]
            available.append({k:d[k] for k in ('kind','leg_id','name')}|{'variants':[{'label':l,**pool(c,owner,d['context_key'],l,repo.generation(c,owner))} for l in labels]})
    return {'items':[data(c,owner,r) for r in rows],'available':available}

router=APIRouter(prefix='/api/v1/trips/{trip_id}/walking-segments')
@router.get('')
def get(request:Request,trip_id:str):
    owner=trips.authenticate(request)
    with database() as c:
        trip=trip_repo.owned(c,owner,parsed_id(trip_id))
        if trip is None:trips.missing()
        return answer(request,read(c,owner,trip))

@router.post('')
def start(request:Request,trip_id:str,body:Start):
    owner=trips.authenticate(request,'segment-start');tid=parsed_id(trip_id)
    with database() as c:
        p=learning.locked(c,owner);trip=trip_repo.owned(c,owner,tid,True)
        if trip is None:trips.missing()
        value=body.model_dump(mode='json');value['occurred_at']=body.occurred_at.astimezone(timezone.utc).isoformat();hashed=digest(value)
        old=repo.start_request(c,owner,body.client_request_id)
        if old:
            if old['trip_id']!=tid or old['start_hash']!=hashed:trips.conflict()
            row=next(r for r in repo.rows(c,owner,trip=tid) if r['id']==old['id']);return answer(request,data(c,owner,row))
        state=read(c,owner,trip);d=next((d for d in descriptors(trip) if d['kind']==body.kind and d['leg_id']==str(body.leg_id)),None)
        if not d or not any(a['kind']==body.kind and a['leg_id']==str(body.leg_id) for a in state['available']):trips.order()
        events=trip_repo.events(c,tid);stage=progress(trip['snapshot']['candidate'],events)
        anchor=next(e for e in events if str(e['id'])==stage['anchor_event_id'])
        now=datetime.now(timezone.utc)
        if not anchor['occurred_at']<=body.occurred_at<=now or (now-body.occurred_at).total_seconds()>60:
            raise AuthError(422,'VALIDATION_ERROR','시작 경계에서 바로 기록해주세요.')
        stats=pool(c,owner,d['context_key'],body.label,p['generation']);seconds=stats['estimate_seconds'];identifier=uuid4()
        repo.insert(c,(identifier,owner,tid,body.kind,body.leg_id,d['context_key'],body.label,p['generation'],body.client_request_id,hashed,
          anchor['id'],body.occurred_at,seconds,body.occurred_at+timedelta(seconds=seconds) if seconds else None,trip['expires_at']))
        return answer(request,data(c,owner,next(r for r in repo.rows(c,owner,trip=tid) if r['id']==identifier)),201)

def mutate(request,trip_id,identifier,body,exclude=False):
    owner=trips.authenticate(request,'segment-confirm');tid=parsed_id(trip_id);identifier=parsed_id(identifier)
    with database() as c:
        learning.locked(c,owner);trip=trip_repo.owned(c,owner,tid,True)
        if trip is None:trips.missing()
        hashed=digest([str(identifier),exclude,body.model_dump(mode='json')]);old=receipts.receipt(c,owner,body.client_request_id)
        if old:
            if old['trip_id']!=tid or old['kind']!='segment' or old['body_hash']!=hashed:trips.conflict()
            return answer(request,old['response'])
        row=next((r for r in repo.rows(c,owner,trip=tid) if r['id']==identifier),None)
        if row is None:trips.missing()
        if row['version']!=body.expected_version:trips.conflict()
        if exclude:
            if trip['status']=='active':raise AuthError(409,'ACTIVE_TRIP_EDIT_FORBIDDEN','종료하거나 취소한 뒤 정정해주세요.')
            repo.exclude(c,identifier,body.excluded)
        else:
            if row['finish_received_at'] is not None:trips.conflict()
            legs=trip['snapshot']['candidate']['ordered_legs'];i=next(i for i,l in enumerate(legs) if l['leg_id']==str(row['leg_id']));walk=legs[i-1]['leg_id'] if i else legs[i]['leg_id']
            ready=next((e for e in trip_repo.events(c,tid) if e['type']=='approach_arrived' and str(e['leg_id'])==walk),None)
            if ready is None:raise AuthError(422,'VALIDATION_ERROR','승차 지점 도착 기록을 먼저 저장해주세요.')
            repo.finish(c,identifier,ready,body)
        result=data(c,owner,next(r for r in repo.rows(c,owner,trip=tid) if r['id']==identifier))
        if not exclude and result['status']=='valid' and body.apply_to_guidance:repo.select(c,owner,row['context_key'],row['label'])
        receipts.save_receipt(c,owner,body.client_request_id,tid,'segment',hashed,result)
        return answer(request,result)

@router.post('/{measurement_id}/confirm')
def confirm(request:Request,trip_id:str,measurement_id:str,body:Confirm):return mutate(request,trip_id,measurement_id,body)
@router.patch('/{measurement_id}')
def exclude(request:Request,trip_id:str,measurement_id:str,body:Exclude):return mutate(request,trip_id,measurement_id,body,True)

def for_guidance(owner,binding,route,connection=None):
    if connection is None:
        with database() as c:return for_guidance(owner,binding,route,c)
    c=connection;p=learning.locked(c,owner)
    trip={'routine_id':binding.routine_id,'snapshot':{'candidate':route,'routine_version':binding.version,'place_refs':list(binding.place_refs)}}
    out=[]
    for d in descriptors(trip):
        label=repo.selected(c,owner,d['context_key'])
        if label is None:continue
        stats=pool(c,owner,d['context_key'],label,p['generation'])
        if stats['estimate_seconds'] is None:continue
        out.append({**{k:d[k] for k in ('kind','leg_id')},'label':label,'source':'manual_history','profile_version':p['version'],**stats})
    return out
