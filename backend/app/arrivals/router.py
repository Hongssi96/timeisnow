from fastapi import APIRouter,Request
from app.arrivals import service
from app.arrivals.dto import Envelope
router=APIRouter(prefix='/api/v1')
@router.get('/journey-searches/{search_id}/candidates/{candidate_id}/first-arrivals',response_model=Envelope)
def first_arrivals(request:Request,search_id:str,candidate_id:str):
    return service.result(request,search_id,candidate_id)
