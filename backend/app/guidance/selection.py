"""Routine selection memory; manual absence is not an observed missed vehicle."""
from collections import OrderedDict
from copy import deepcopy
from dataclasses import dataclass,field
from datetime import timedelta
from threading import Lock
from app.arrivals import service as arrivals,cache
from app.common.database import database
from app.common.errors import AuthError
from app.trips import repository

@dataclass
class Session:
    expires_at:object
    identity:object=None
    value:dict=field(default_factory=lambda:{'anchor':None,'skipped':set()})
    lock:object=field(default_factory=Lock)

_states=OrderedDict()
_guard=Lock()

def limited():raise AuthError(429,'RATE_LIMITED','출발 안내를 확인 중이에요. 잠시 후 다시 확인해주세요.',headers={'Retry-After':'2'})

def observation(binding):
    from app.guidance.routine import signature
    with database() as c:row=repository.selection_observation(c,binding.user_id,binding.routine_id)
    if row is None:return None,False
    marker=tuple(row[k] for k in ('id','version','event_id','event_version','source','type','excluded'))
    snap=row['snapshot']
    matching=(snap.get('routine_version')==binding.version
        and tuple(tuple(ref) for ref in snap.get('place_refs',[]))==binding.place_refs
        and signature(snap['candidate'])==binding.signature)
    reported=matching and row['event_id'] is not None and row['type']=='departed' and row['source']=='manual' and row['excluded'] is False
    return marker,reported

def begin(binding):
    at=arrivals.now();key=(str(binding.user_id),str(binding.routine_id))
    with _guard:
        for old in list(_states):
            if _states[old].expires_at<=at and not _states[old].lock.locked():del _states[old]
        entry=_states.get(key)
        if entry is None:
            if len(_states)>=128:
                victim=next((k for k,v in _states.items() if not v.lock.locked()),None)
                if victim is None:limited()
                del _states[victim]
            entry=Session(at+timedelta(seconds=120));_states[key]=entry
        if not entry.lock.acquire(blocking=False):limited()
        _states.move_to_end(key)
    try:return Lease(entry,binding)
    except BaseException:entry.lock.release();raise

class Lease:
    def __init__(self,entry,binding):
        self.entry=entry;self.binding=binding
        self.identity=(binding.version,str(binding.plan_id),binding.signature,binding.place_refs)
        self.pending=deepcopy(entry.value) if entry.identity==self.identity else {'anchor':None,'skipped':set()}
        self.before,self.reported=observation(binding)
        self.aliases={};self.scope=None;self.profile=None;self.walking=None

    def choose(self,evidence,walking,profile,at,fingerprint):
        if self.reported:return {'reported':True}
        value=arrivals.project(evidence,at)
        if not value.valid_for_guidance or walking is None:return None
        entry=cache.lookup(self.binding.user_id,value.search_id,value.candidate_id,fingerprint,at)
        if entry is None or entry.mapping is None or entry.evidence is None or entry.evidence.received_at!=value.received_at:
            return {'blocked':True,'reason':'SELECTION_IDENTITY_UNCONFIRMED'}
        self.aliases=dict(entry.vehicle_keys)
        if any(str(item.candidate_id) not in self.aliases for item in value.candidates):
            return {'blocked':True,'reason':'SELECTION_IDENTITY_UNCONFIRMED'}
        m=entry.mapping
        self.scope=(m.provider,m.station_id,m.route_id,m.sta_order,m.route_dest_id,m.mapping_version)
        self.profile=dict(profile);self.walking=walking
        anchor=self.pending['anchor']
        if anchor and (anchor['eta']<=at or anchor['profile']!=profile or anchor['walking']!=walking or anchor['scope']!=self.scope):
            self.pending={'anchor':None,'skipped':set()};anchor=None
        ordered=sorted(value.candidates,key=lambda item:(item.predicted_arrival_at,str(item.candidate_id)))
        if anchor and at-anchor['s']>timedelta(seconds=anchor['walking']/2):
            if len(self.pending['skipped'])>=16:return {'blocked':True,'reason':'SELECTION_HISTORY_LIMIT'}
            self.pending['skipped'].add(anchor['vehicle'])
            current=next((item for item in ordered if self.aliases[str(item.candidate_id)]==anchor['vehicle']),None)
            cutoff=current.predicted_arrival_at if current else anchor['eta']
            options=[item for item in ordered if self.aliases[str(item.candidate_id)] not in self.pending['skipped']
                and item.predicted_arrival_at>cutoff and (item.predicted_arrival_at-at).total_seconds()>=walking+profile['buffer']]
            if len(self.pending['skipped'])>=16:return {'blocked':True,'reason':'SELECTION_HISTORY_LIMIT'}
            if not options:return {'blocked':True,'reason':'DEPARTURE_UNCONFIRMED_NO_NEXT'}
            return {'candidate_id':str(options[0].candidate_id),'reason':'DEPARTURE_UNCONFIRMED_NEXT_VEHICLE'}
        allowed=[item for item in ordered if self.aliases[str(item.candidate_id)] not in self.pending['skipped']]
        if not allowed:return {'blocked':True,'reason':'DEPARTURE_UNCONFIRMED_NO_NEXT'}
        current=next((item for item in allowed if anchor and self.aliases[str(item.candidate_id)]==anchor['vehicle']
            and (item.predicted_arrival_at-at).total_seconds()>=walking),None)
        chosen=current or next((item for item in allowed if (item.predicted_arrival_at-at).total_seconds()>=walking),allowed[0])
        return {'candidate_id':str(chosen.candidate_id)}

    def commit(self,value):
        if observation(self.binding)!=(self.before,self.reported):
            raise AuthError(409,'VERSION_CONFLICT','출발 확인이나 이동 상태가 변경됐어요. 다시 확인해주세요.')
        if self.reported:self.pending={'anchor':None,'skipped':set()}
        elif value.valid_for_guidance:
            vehicle=self.aliases.get(str(value.arrival_candidate_id))
            if vehicle is None:return
            self.pending['anchor']={'vehicle':vehicle,'s':value.recommended_departure_at,'eta':value.vehicle_arrival_at,
                'walking':self.walking,'profile':self.profile,'scope':self.scope}
        self.entry.identity=self.identity;self.entry.value=self.pending
        anchor=self.pending['anchor']
        self.entry.expires_at=anchor['eta'] if anchor else arrivals.now()+timedelta(seconds=120)

    def close(self):self.entry.lock.release()
