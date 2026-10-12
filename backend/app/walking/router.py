from fastapi import APIRouter, Request

from app.walking import service, history_service
from app.walking.dto import EvidenceEnvelope
from app.walking.history_dto import EstimateEnvelope

router = APIRouter(prefix='/api/v1')


@router.get('/journey-searches/{search_id}/candidates/{candidate_id}/walking-evidence',
            response_model=EvidenceEnvelope)
def walking_evidence(request: Request, search_id: str, candidate_id: str):
    return service.result(request, search_id, candidate_id)



@router.get('/walking-estimates/{estimate_id}',response_model=EstimateEnvelope)
def walking_estimate(request: Request,estimate_id: str):
    return history_service.detail(request,estimate_id)
