"""Journey endpoints; admission and worker flows live in service."""
from fastapi import APIRouter, BackgroundTasks, Request

from app.common.response import answer
from app.journeys import service
from app.journeys.dto import SearchInput
from app.journeys.models import SearchEnvelope

router = APIRouter(prefix='/api/v1')


@router.post('/journey-searches', status_code=202)
def search(request: Request, body: SearchInput, background: BackgroundTasks):
    outcome = service.search(request, body)
    if outcome[0] == 'replay':
        return outcome[1]
    _, data, task = outcome
    background.add_task(service.execute, *task)
    return answer(request, data, 202)


@router.get('/journey-searches/{search_id}', response_model=SearchEnvelope)
def result(request: Request, search_id: str):
    return service.result(request, search_id)


@router.get('/jobs/{job_id}')
def job_result(request: Request, job_id: str):
    return service.job_result(request, job_id)
