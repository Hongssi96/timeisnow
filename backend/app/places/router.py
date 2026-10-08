"""Place endpoints; flows live in service, envelope assembled here."""
from fastapi import APIRouter, Query, Request
from fastapi.responses import Response

from app.common.response import answer
from app.places import service
from app.places.dto import ConfirmationInput, PlaceInput, PlaceUpdateInput, SearchInput

router = APIRouter(prefix='/api/v1')


@router.get('/map-config')
def map_config(request: Request):
    return answer(request, service.map_config(request))


@router.post('/place-location-confirmations')
def confirm(request: Request, body: ConfirmationInput):
    return answer(request, service.confirm(request, body))


@router.post('/place-searches')
def search(request: Request, body: SearchInput):
    return answer(request, service.search(request, body))


@router.post('/places')
def create(request: Request, body: PlaceInput):
    return answer(request, service.create(request, body), 201)


@router.patch('/places/{place_id}')
def update(request: Request, place_id: str, body: PlaceUpdateInput):
    return answer(request, service.update(request, place_id, body))


@router.delete('/places/{place_id}')
def delete(request: Request, place_id: str):
    service.delete(request, place_id)
    return Response(status_code=204, headers={'Cache-Control': 'no-store'})


@router.get('/places')
def listing(request: Request, limit: int = Query(default=20, ge=1, le=100), cursor: str | None = None):
    return answer(request, service.listing(request, limit, cursor))


@router.get('/places/{place_id}')
def detail(request: Request, place_id: str):
    return answer(request, service.detail(request, place_id))
