from typing import Literal
from fastapi import APIRouter,Request,BackgroundTasks,Query
from app.guidance import service
from app.guidance.dto import DepartureEnvelope
from app.guidance import routine
router=APIRouter(prefix='/api/v1')
@router.get('/journey-searches/{search_id}/candidates/{candidate_id}/first-departure',response_model=DepartureEnvelope)
def first_departure(request:Request,search_id:str,candidate_id:str,departure_basis:Literal['recommended','now']='recommended',include_connections:bool=False):
    return service.result(request,search_id,candidate_id,departure_basis,include_connections)

@router.post('/routines/{routine_id}/departure-searches',status_code=202)
def routine_search(request:Request,routine_id:str,body:routine.RefreshInput,background:BackgroundTasks):
    return routine.refresh(request,routine_id,body,background)

@router.get('/routines/{routine_id}/departure-searches/{search_id}/first-departure')
def routine_departure(request:Request,routine_id:str,search_id:str,expected_version:int=Query(ge=1)):
    return routine.result(request,routine_id,search_id,expected_version)
