from fastapi import APIRouter, Request

from app.walking import service
from app.walking.dto import EvidenceEnvelope

router = APIRouter(prefix='/api/v1')


@router.get('/journey-searches/{search_id}/candidates/{candidate_id}/walking-evidence',
            response_model=EvidenceEnvelope)
def walking_evidence(request: Request, search_id: str, candidate_id: str):
    return service.result(request, search_id, candidate_id)
