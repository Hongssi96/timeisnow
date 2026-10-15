from typing import Literal
from fastapi import APIRouter,Request,Query,BackgroundTasks
from app.trips import dto,service
router=APIRouter(prefix='/api/v1/trips')

@router.post('',status_code=201)
def create(request:Request,body:dto.Create):return service.create(request,body)
@router.get('')
def listed(request:Request,limit:int=Query(default=20,ge=1,le=100),cursor:str|None=None,routine_id:str|None=None,status:Literal['active','cancelled','missed','completed']|None=None):
    return service.listed(request,limit,cursor,routine_id,status)
@router.get('/{trip_id}')
def detail(request:Request,trip_id:str):return service.detail(request,trip_id)
@router.post('/{trip_id}/events',status_code=201)
def event(request:Request,trip_id:str,body:dto.Event):return service.add_event(request,trip_id,body)
@router.patch('/{trip_id}')
def cancel(request:Request,trip_id:str,body:dto.Cancel):return service.cancel(request,trip_id,body)

@router.post('/{trip_id}/remaining-searches',status_code=202)
def remaining_search(request:Request,trip_id:str,body:dto.RemainingSearch,background:BackgroundTasks):
    from app.guidance import remaining
    return remaining.refresh(request,trip_id,body,background)

@router.get('/{trip_id}/remaining-searches/{search_id}/guidance')
def remaining_guidance(request:Request,trip_id:str,search_id:str,expected_version:int=Query(ge=1)):
    from app.guidance import remaining
    return remaining.result(request,trip_id,search_id,expected_version)
