"""FastAPI entry point. Business endpoints are added in subsequent TODO tasks."""

import uuid
import re
from datetime import datetime, timezone
from time import perf_counter

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException
from app.request_logging import record_request
from app.auth import router as auth_router, AuthError
from app.places import router as places_router
from app.origins import router as origins_router
from app.journeys import router as journeys_router

app = FastAPI(title="지금이니? API", version="0.1.0")
app.include_router(auth_router)
app.include_router(places_router)
app.include_router(origins_router)
app.include_router(journeys_router)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def error_response(request, status, code, message, details=None, headers=None):
    request.state.error_code = code
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message, "details": details or []},
                 "meta": {"request_id": request.state.request_id, "server_time": utc_now_iso()}},
        headers=headers,
    )


@app.exception_handler(AuthError)
async def auth_error(request: Request, exception: AuthError):
    return error_response(request, exception.status, exception.code, exception.message,
                          headers={'Cache-Control': 'no-store', **(exception.headers or {})})


@app.middleware("http")
async def request_identity(request: Request, call_next):
    started_at = perf_counter()
    request.state.request_id = f"req_{uuid.uuid4().hex}"
    unexpected = None
    try:
        response = await call_next(request)
    except Exception as exception:
        unexpected = exception
        # Only the exception class is logged; no message or traceback.
        response = error_response(request, 500, "INTERNAL_ERROR", "처리를 완료할 수 없습니다.")
    response.headers["X-Request-ID"] = request.state.request_id
    if (request.url.path.startswith('/api/v1/auth/') or request.url.path == '/api/v1/me'
            or request.url.path in ('/api/v1/place-searches', '/api/v1/map-config', '/api/v1/place-location-confirmations', '/api/v1/origin-validations')
            or request.url.path.startswith(('/api/v1/places', '/api/v1/journey-searches', '/api/v1/jobs'))):
        response.headers['Cache-Control'] = 'no-store'
    record_request(request, response.status_code, started_at, unexpected)
    return response


@app.exception_handler(HTTPException)
async def http_error(request: Request, exception: HTTPException):
    codes = {401: "AUTH_REQUIRED", 404: "RESOURCE_NOT_FOUND", 405: "METHOD_NOT_ALLOWED",
             422: "VALIDATION_ERROR", 429: "RATE_LIMITED", 500: "INTERNAL_ERROR"}
    return error_response(request, exception.status_code, codes.get(exception.status_code, "HTTP_ERROR"),
                          "요청을 처리할 수 없습니다.", headers=exception.headers)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exception: RequestValidationError):
    details = []
    for error in exception.errors():
        parts = [str(part) for part in error.get("loc", ())]
        field = ".".join(parts) if all(re.fullmatch(r"[A-Za-z0-9_]{1,64}", part) for part in parts) else "request"
        details.append({"field": field, "reason": "입력 형식을 확인해주세요."})
    return error_response(request, 422, "VALIDATION_ERROR", "입력값을 확인해주세요.", details)


@app.get("/api/v1/health")
def health(request: Request) -> JSONResponse:
    # 계약(api_contract 01절): 200 {status, server_time}. DB·키 등 내부 정보는 노출하지 않는다.
    now = utc_now_iso()
    request_id = request.state.request_id
    return JSONResponse(
        content={
            "data": {"status": "ok", "server_time": now},
            "meta": {"request_id": request_id, "server_time": now},
        },
        headers={"X-Request-ID": request_id},
    )
