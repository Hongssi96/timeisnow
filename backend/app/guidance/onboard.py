"""Explicit manual vehicle match and same-vehicle official alighting prediction."""
from collections import OrderedDict
from dataclasses import dataclass,field
from datetime import timedelta
from threading import Lock
from uuid import UUID
import hashlib,math,re,time
from pydantic import BaseModel,ConfigDict,Field,StrictInt
from app.arrivals import cache,mapping,provider,service as arrivals
from app.arrivals.dto import Mapping
from app.arrivals.matching import direction_candidate
from app.common.database import database
from app.common.errors import AuthError
from app.common.response import answer
from app.common.timeutil import iso
from app.guidance import routine,service as departure
from app.trips import service as trips,repository as repo
from app.trips.progress import state as progress_state

class Confirmation(BaseModel):
    model_config=ConfigDict(extra='forbid')
    expected_version:StrictInt=Field(ge=1)
    anchor_event_id:UUID
    leg_id:UUID
    plate_suffix:str=Field(strict=True,pattern=r'^[0-9]{4}$')

@dataclass
class Entry:
    expires:object
    lock:object=field(default_factory=Lock)
    vehicle:object=None
    suffix_hash:object=None
    confirmed_until:object=None
    mapping:object=None
    mapping_until:object=None
    stations:dict=field(default_factory=dict)
    evidence:object=None
    attempted_at:object=None

_entries=OrderedDict()
_guard=Lock()

def collect(owner,search_id,candidate):
    """Copy only already verified public identities, never raw endpoint geometry."""
    at=arrivals.now();root=cache.lookup(owner,search_id,candidate['candidate_id'],cache.fingerprint(candidate),at)
    if root is None:return {}
    result={}
    for leg in candidate['ordered_legs']:
        if leg['type']!='BUS':continue
        entry=root if str(leg['leg_id'])==root.context['first_leg_id'] else cache.following_entry(root,leg['leg_id'])
        if entry is None or entry.mapping is None or entry.boarding_endpoint is None:continue
        try:m=arrivals.checked_mapping(entry.mapping,leg,at)
        except AuthError:continue
        end=entry.boarding_endpoint
        order=end.get('alighting_order')
        if end.get('mapping_identity')!=cache.mapping_identity(m) or type(order) is not int or not m.sta_order<order<=1000:continue
        result[str(leg['leg_id'])]={'route_id':m.route_id,'board_station_id':m.station_id,'board_order':m.sta_order,
            'alight_station_id':end['alighting_station_id'],'alight_order':order,'route_dest_id':m.route_dest_id}
    return result

def source(owner,tid,version):
    with database() as c:
        row=repo.owned(c,owner,tid)
        if row is None:trips.missing()
        progress=progress_state(row['snapshot']['candidate'],repo.events(c,tid))
    if row['status']!='active' or row['version']!=version or progress['stage']!='onboard':
        raise AuthError(409,'VERSION_CONFLICT','현재 탑승 중인 이동을 다시 확인해주세요.')
    snap=row['snapshot'];r,plan,places=routine.current(owner,row['routine_id'],snap['routine_version'])
    refs=tuple((str(p['id']),p['location_version']) for p in places)
    profile=departure.settings(owner)
    if tuple(tuple(v) for v in snap['place_refs'])!=refs or routine.signature(plan['candidate'])!=routine.signature(snap['candidate']) or profile['version']!=snap['departure']['profile_version']:
        raise AuthError(409,'VERSION_CONFLICT','루틴·장소·개인 설정이 변경됐어요.')
    return row,progress,profile

def checked(owner,tid,version,initial):
    current=source(owner,tid,version)
    if current[1]!=initial[1] or current[2]!=initial[2]:raise AuthError(409,'VERSION_CONFLICT','탑승 구간이 변경됐어요.')

def entry_for(owner,tid,progress,expires):
    at=arrivals.now();key=(owner,tid,progress['anchor_event_id'])
    with _guard:
        for k in list(_entries):
            if _entries[k].expires<=at:del _entries[k]
        if key not in _entries:_entries[key]=Entry(min(expires,at+timedelta(minutes=30)))
        _entries.move_to_end(key)
        while len(_entries)>32:_entries.popitem(last=False)
        return _entries[key]

def base(row,progress,at,expiry,reason):
    return {'model_version':'trip.onboard.v1','trip_id':str(row['id']),'trip_version':row['version'],
        'current_leg_id':progress['current_leg_id'],'anchor_event_id':progress['anchor_event_id'],
        'status':'needs_data','source':'manual_vehicle_match','timing_basis':'receipt_estimate',
        'source_status':'unknown','generated_at':None,'received_at':None,'expires_at':iso(min(expiry,at+timedelta(seconds=60))),
        'estimated_alighting_at':None,'remaining_seconds':None,'reasons':[reason]}

def project(data,at):
    value=dict(data)
    if value['status']=='estimated':
        from datetime import datetime
        eta=datetime.fromisoformat(value['estimated_alighting_at'].replace('Z','+00:00'))
        end=datetime.fromisoformat(value['expires_at'].replace('Z','+00:00'))
        remaining=math.floor((eta-at).total_seconds())
        received=datetime.fromisoformat(value['received_at'].replace('Z','+00:00'))
        if at<received or at>end or remaining<=0:
            value.update(status='needs_data',estimated_alighting_at=None,remaining_seconds=None,reasons=['ONBOARD_EVIDENCE_EXPIRED'])
        else:value['remaining_seconds']=remaining
    return value

def route_map(binding,leg_id,entry,deadline):
    at=arrivals.now()
    if entry.mapping is not None and entry.mapping.verified_at<=at<entry.mapping_until:return entry.mapping
    rows=mapping.query('stops',{'routeId':binding['route_id']},deadline)
    direction=direction_candidate(binding,rows,None,binding)
    if direction['status']!='direction_candidate' or direction['route_dest_id']!=binding['route_dest_id']:return None
    entry.mapping_until=arrivals.now()+timedelta(seconds=300)
    entry.stations={int(r['stationSeq']):provider.numeric_id(r['stationId']) for r in rows}
    entry.mapping=Mapping(provider='gyeonggi-bus',first_leg_id=UUID(leg_id),station_id=binding['alight_station_id'],
        route_id=binding['route_id'],sta_order=binding['alight_order'],route_dest_id=binding['route_dest_id'],
        mapping_version='gbis.onboard.v1',verified_at=arrivals.now(),valid_until=entry.mapping_until)
    return entry.mapping

def vehicles(rows,binding,stations):
    result=[];seen=set()
    for row in rows:
        vehicle=provider.numeric_id(row.get('vehId'));station=provider.numeric_id(row.get('stationId'))
        seq=provider.numeric_id(row.get('stationSeq'));state=provider.numeric_id(row.get('stateCd'));plate=row.get('plateNo')
        if provider.numeric_id(row.get('routeId'))!=binding['route_id'] or not vehicle or vehicle=='0' or vehicle in seen:provider.invalid()
        seen.add(vehicle)
        if not seq or int(seq)>1000 or stations.get(int(seq))!=station or state not in ('0','1','2'):provider.invalid()
        if not isinstance(plate,str) or re.fullmatch(r'[가-힣A-Za-z0-9 ]{4,20}',plate) is None or re.search(r'[0-9]{4}$',plate) is None:continue
        result.append((vehicle,plate[-4:],int(seq)))
    return result

def result(request,trip_id,version,body=None):
    owner=trips.authenticate(request,'event' if body is not None else None);tid=arrivals.parsed_id(trip_id)
    initial=source(owner,tid,version);row,p,profile=initial;at=arrivals.now()
    if body is not None and (str(body.leg_id)!=p['current_leg_id'] or str(body.anchor_event_id)!=p['anchor_event_id']):
        raise AuthError(409,'VERSION_CONFLICT','현재 탑승 구간을 다시 확인해주세요.')
    entry=entry_for(owner,tid,p,row['expires_at'])
    def missing(reason):return base(row,p,arrivals.now(),entry.expires,reason)
    if not entry.lock.acquire(blocking=False):raise AuthError(429,'RATE_LIMITED','차량 정보를 확인 중이에요.',{'Retry-After':'2'})
    try:
        digest=hashlib.sha256((str(owner)+str(tid)+body.plate_suffix).encode()).hexdigest() if body is not None else None
        if body is None and (entry.vehicle is None or entry.confirmed_until<=at):return answer(request,missing('VEHICLE_CONFIRMATION_REQUIRED'))
        if body is not None and digest!=entry.suffix_hash:
            entry.vehicle=None;entry.evidence=None;entry.attempted_at=None
        if entry.evidence is not None and entry.attempted_at is not None and at-entry.attempted_at<timedelta(seconds=60):
            checked(owner,tid,version,initial);return answer(request,project(entry.evidence,at))
        binding=row['snapshot'].get('transit_bindings',{}).get(p['current_leg_id'])
        if binding is None:return answer(request,missing('ONBOARD_MAPPING_REQUIRED'))
        arrivals.reserve_refresh(owner);deadline=time.monotonic()+20
        entry.evidence=None;entry.attempted_at=at
        m=route_map(binding,p['current_leg_id'],entry,deadline)
        value=missing('ONBOARD_MAPPING_UNCONFIRMED')
        if m is not None:
            rows=mapping.query('locations',{'routeId':m.route_id},deadline);location_at=arrivals.now()
            values=vehicles(rows,binding,entry.stations)
            matches=[v for v in values if v[1]==body.plate_suffix] if body is not None else [v for v in values if v[0]==entry.vehicle]
            value=missing('VEHICLE_UNCONFIRMED')
            if len(matches)==1 and binding['board_order']<=matches[0][2]<binding['alight_order']:
                vehicle=matches[0][0]
                predictions=provider.fetch(m);received=arrivals.now()
                selected=[seconds for key,seconds in predictions or [] if key==vehicle]
                value=missing('SAME_VEHICLE_ARRIVAL_MISSING')
                checked(owner,tid,version,initial)
                if body is not None:
                    entry.vehicle=vehicle;entry.suffix_hash=digest
                    entry.expires=min(row['expires_at'],arrivals.now()+timedelta(minutes=30));entry.confirmed_until=entry.expires
                if len(selected)==1:
                    eta=received+timedelta(seconds=selected[0]);expiry=min(entry.expires,entry.confirmed_until,entry.mapping_until,location_at+timedelta(seconds=120),received+timedelta(seconds=120))
                    value.update(status='estimated',received_at=iso(min(location_at,received)),expires_at=iso(expiry),
                        estimated_alighting_at=iso(eta),remaining_seconds=selected[0],reasons=['SAME_VEHICLE_PROVIDER_ESTIMATE'])
        if time.monotonic()>deadline:raise AuthError(504,'PROVIDER_TIMEOUT','차량 조회 시간이 지났어요.')
        checked(owner,tid,version,initial)
        entry.evidence=value;entry.attempted_at=arrivals.now()
        return answer(request,project(value,arrivals.now()))
    finally:entry.lock.release()
