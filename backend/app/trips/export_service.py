"""Authenticated virtual files: read current records, never retain a private copy."""
from datetime import datetime,timedelta,timezone
from uuid import uuid4
from typing import Literal
from pydantic import BaseModel,ConfigDict,AwareDatetime,Field,field_validator
from fastapi import APIRouter,Request
from app.common.database import database
from app.common.errors import AuthError
from app.common.response import answer
from app.common.timeutil import iso
from app.places.service import parsed_id
from app.trips import service,repository as trips,export_repository as repo

class Export(BaseModel):
    model_config=ConfigDict(extra='forbid')
    from_:AwareDatetime|None=Field(default=None,alias='from')
    to:AwareDatetime|None=None
    format:Literal['json']

    @field_validator('from_','to',mode='before')
    @classmethod
    def text(cls,value):
        if not isinstance(value,str):raise ValueError('ISO timestamp required')
        return value

def bounded(rows):
    if len(rows)>500:
        raise AuthError(422,'EXPORT_LIMIT_EXCEEDED','기록이 500건을 넘어요. 더 짧은 기간을 선택해주세요.')
    return rows

def metadata(row):
    return {'job_id':str(row['id']),'status':'succeeded','error':None,
      'result_ref':f"/api/v1/trip-exports/{row['id']}/download" if row['download_expires_at']>datetime.now(timezone.utc) else None,
      'finished_at':iso(row['created_at']),'expires_at':iso(row['expires_at']),
      'download_expires_at':iso(row['download_expires_at'])}

def authenticate(request,kind=None):
    owner=service.authenticate(request,kind)
    # Commit expiry cleanup even when the subsequent resource lookup returns 404.
    with database() as c:repo.clean(c,owner)
    return owner

def job(request,job_id,optional=False):
    owner=authenticate(request)
    with database() as c:
        repo.clean(c,owner)
        row=repo.owned(c,owner,parsed_id(job_id))
        if row is None:
            if optional:return None
            service.missing()
        return answer(request,metadata(row))

router=APIRouter(prefix='/api/v1/trip-exports')

@router.post('',status_code=202)
def create(request:Request,body:Export):
    owner=authenticate(request,'create-export')
    now=datetime.now(timezone.utc)
    start=body.from_ or now-timedelta(days=90)
    end=body.to or now
    if not start<end or end-start>timedelta(days=90):
        raise AuthError(422,'VALIDATION_ERROR','조회 기간은 시작 이후부터 최대 90일까지예요.')
    with database() as c:
        trips.lock_owner(c,owner);repo.clean(c,owner)
        bounded(repo.rows(c,owner,start,end,now))
        return answer(request,metadata(repo.create(c,owner,uuid4(),start,end)),202)

@router.get('/{job_id}')
def result(request:Request,job_id:str):return job(request,job_id)

@router.get('/{job_id}/download')
def download(request:Request,job_id:str):
    owner=authenticate(request)
    with database() as c:
        trips.lock_owner(c,owner);repo.clean(c,owner)
        row=repo.owned(c,owner,parsed_id(job_id))
        if row is None or row['download_expires_at']<=datetime.now(timezone.utc):service.missing()
        records=[]
        for trip in bounded(repo.rows(c,owner,row['range_from'],row['range_to'],row['created_at'])):
            observation=repo.observation(c,owner,trip['id'])
            records.append({
              'trip_id':str(trip['id']),**{k:trip[k] for k in ('measurement_mode','status','version')},
              **{k:trip[k].astimezone(timezone.utc).isoformat() for k in ('created_at','expires_at')},
              'events':[service.event_data(e) for e in trips.events(c,trip['id'])],
              'corrections':[{'correction_id':str(a['id']),'reason':a['reason'],
                'previous':a['previous_value'],'current':a['new_value'],'corrected_at':iso(a['created_at'])}
                for a in repo.corrections(c,trip['id'])],
              'walking_observation':None if observation is None else {**observation['response'],
                'version':observation['version'],'confirmation':observation['confirmation']}})
        response=answer(request,{'schema_version':'trip-export.v1','generated_at':iso(datetime.now(timezone.utc)),
          'range':{key:row[column].astimezone(timezone.utc).isoformat() for key,column in [('from','range_from'),('to','range_to')]},'records':records})
        response.headers['Content-Disposition']='attachment; filename="timeisnow-trip-records.json"'
        response.headers['X-Content-Type-Options']='nosniff'
        return response
