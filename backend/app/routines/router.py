"""Routine endpoints; flows live in service, envelope assembled here."""
from fastapi import APIRouter, Query, Request
from fastapi.responses import Response

from app.common.response import answer
from app.routines import service
from app.routines.dto import RoutineInput, RoutineScheduleInput

router = APIRouter(prefix='/api/v1')


@router.post('/routines', status_code=201)
def create(request: Request, body: RoutineInput):
    return answer(request, service.create(request, body), 201)


@router.get('/routines')
def listing(request: Request, limit: int = Query(default=20, ge=1, le=100), cursor: str | None = None):
    return answer(request, service.listing(request, limit, cursor))


@router.get('/routines/{routine_id}')
def detail(request: Request, routine_id: str):
    return answer(request, service.detail(request, routine_id))


@router.patch('/routines/{routine_id}')
def update(request: Request, routine_id: str, body: RoutineScheduleInput):
    return answer(request, service.update(request, routine_id, body))


@router.delete('/routines/{routine_id}')
def delete(request: Request, routine_id: str):
    service.delete(request, routine_id)
    return Response(status_code=204, headers={'Cache-Control': 'no-store'})
