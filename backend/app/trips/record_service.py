"""Atomic owned record correction/deletion and surviving-sample rebuild."""
import hashlib,json
from datetime import datetime,timezone
from app.common.database import database
from app.common.errors import AuthError
from app.common.response import answer
from app.common.timeutil import iso
from app.places.service import parsed_id
from app.trips import repository as trips,service,record_repository as repo
from app.personalization import repository as learning,service as personalization,relearning

def observation_data(row):
    return {**row['response'],'version':row['version'],'confirmation':row['confirmation']} if row else None

def editable(trip):
    if trip['status']=='active':raise AuthError(409,'ACTIVE_TRIP_EDIT_FORBIDDEN','진행 중인 이동을 종료하거나 취소한 뒤 정정해주세요.')

def begin(c,owner,tid,body,kind,target):
    p=learning.locked(c,owner)
    value=body.model_dump(mode='json')
    if 'occurred_at' in value and value['occurred_at'] is not None:value['occurred_at']=body.occurred_at.astimezone(timezone.utc).isoformat()
    digest=hashlib.sha256(json.dumps([kind,str(target),value],sort_keys=True).encode()).hexdigest()
    previous=repo.receipt(c,owner,body.client_request_id)
    if previous:
        if previous['body_hash']!=digest or str(previous['trip_id'])!=str(tid):personalization.conflicting()
        return p,None,digest,previous['response']
    trip=trips.owned(c,owner,tid,True)
    if trip is None:service.missing()
    return p,trip,digest,None

def rebuilt(c,owner,p,observation):
    # Even an old-generation sample may have influenced a manually restored factor.
    return relearning.rebuild(c,owner,p) if observation is not None else p

def correct(request,trip_id,event_id,body):
    owner=service.authenticate(request,'record-edit');tid=parsed_id(trip_id);eid=parsed_id(event_id)
    with database() as c:
        p,trip,digest,replay=begin(c,owner,tid,body,'event',eid)
        if replay is not None:return answer(request,replay)
        editable(trip);events=trips.events(c,tid);event=next((e for e in events if e['id']==eid),None)
        if event is None:service.missing()
        if event['version']!=body.expected_version:service.conflict()
        occurred=body.occurred_at or event['occurred_at'];excluded=event['excluded'] if body.excluded is None else body.excluded
        index=events.index(event)
        lower=events[index-1]['occurred_at'] if index else datetime.fromisoformat(trip['snapshot']['departure']['calculated_at'].replace('Z','+00:00'))
        upper=min(event['received_at'],events[index+1]['occurred_at']) if index+1<len(events) else event['received_at']
        if not lower<=occurred<=upper:raise AuthError(422,'VALIDATION_ERROR','정정 시각은 안내·앞뒤 기록·최초 수신시각 범위 안이어야 해요.')
        row=repo.edit(c,event,occurred,excluded,body.correction_reason);version=repo.bump(c,tid)
        old=relearning.refresh(c,owner,trip,p);p=rebuilt(c,owner,p,old)
        result={'event':service.event_data(row),'trip_version':version,'personalization':personalization.summary(c,owner,p)}
        repo.save_receipt(c,owner,body.client_request_id,tid,'event',digest,result)
        return answer(request,result)

def conditions(request,trip_id,body):
    owner=service.authenticate(request,'record-edit');tid=parsed_id(trip_id)
    with database() as c:
        p,trip,digest,replay=begin(c,owner,tid,body,'conditions',tid)
        if replay is not None:return answer(request,replay)
        editable(trip);old=learning.previous(c,owner,tid)
        if old is None:service.missing()
        if old['version']!=body.expected_version:service.conflict()
        relearning.refresh(c,owner,trip,p,{'same_scope':body.same_scope,'condition':body.condition});repo.bump(c,tid)
        p=rebuilt(c,owner,p,old)
        result={'observation':observation_data(learning.previous(c,owner,tid)),'personalization':personalization.summary(c,owner,p)}
        repo.save_receipt(c,owner,body.client_request_id,tid,'conditions',digest,result)
        return answer(request,result)

def observation(request,trip_id):
    owner=service.authenticate(request)
    with database() as c:
        tid=parsed_id(trip_id)
        if trips.owned(c,owner,tid) is None:service.missing()
        return answer(request,observation_data(learning.previous(c,owner,tid)))

def remove(request,trip_id,body):
    owner=service.authenticate(request,'record-delete');tid=parsed_id(trip_id)
    with database() as c:
        p,trip,digest,replay=begin(c,owner,tid,body,'delete',tid)
        if replay is not None:return answer(request,replay)
        if trip['version']!=body.expected_version:service.conflict()
        old=learning.previous(c,owner,tid);repo.remove(c,owner,trip);p=rebuilt(c,owner,p,old)
        result={'trip_id':str(tid),'deleted':True,'personalization':personalization.summary(c,owner,p)}
        repo.save_receipt(c,owner,body.client_request_id,tid,'delete',digest,result,trip['guidance_id'])
        return answer(request,result)

def correction_data(c,tid):
    return [{'correction_id':str(r['id']),'reason':r['reason'],'previous':r['previous_value'],
      'current':r['new_value'],'corrected_at':iso(r['created_at'])} for r in repo.corrections(c,tid)]
