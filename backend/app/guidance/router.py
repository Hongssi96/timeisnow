from typing import Literal
from fastapi import APIRouter,Request
from app.guidance import service
from app.guidance.dto import DepartureEnvelope
router=APIRouter(prefix='/api/v1')
@router.get('/journey-searches/{search_id}/candidates/{candidate_id}/first-departure',response_model=DepartureEnvelope)
def first_departure(request:Request,search_id:str,candidate_id:str,departure_basis:Literal['recommended','now']='recommended'):
    return service.result(request,search_id,candidate_id,departure_basis)
