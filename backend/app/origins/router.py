"""Origin validation endpoint; flow lives in service."""
from fastapi import APIRouter, Request

from app.common.response import answer
from app.origins import service
from app.origins.dto import OriginInput

router = APIRouter(prefix='/api/v1')


@router.post('/origin-validations')
def validate_origin(request: Request, body: OriginInput):
    return answer(request, service.validate(request, body))
