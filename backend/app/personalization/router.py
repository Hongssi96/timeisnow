from typing import Literal
from uuid import UUID
from fastapi import APIRouter,Request
from pydantic import BaseModel,ConfigDict,StrictBool,StrictInt,Field
from app.personalization import service

class Observation(BaseModel):
    model_config=ConfigDict(extra='forbid')
    same_scope:StrictBool
    condition:Literal['normal','running','detour','errand','late_input']

class Mutation(BaseModel):
    model_config=ConfigDict(extra='forbid')
    expected_version:StrictInt=Field(ge=1)
    client_request_id:UUID

router=APIRouter(prefix='/api/v1')
@router.get('/me/personalization')
def get(request:Request):return service.get(request)
@router.post('/me/personalization/reset')
def reset(request:Request,body:Mutation):return service.mutate(request,body,'reset')
@router.post('/me/personalization/restore')
def restore(request:Request,body:Mutation):return service.mutate(request,body,'restore')
@router.post('/trips/{trip_id}/walking-observation')
def observe(request:Request,trip_id:str,body:Observation):return service.observe(request,trip_id,body)
