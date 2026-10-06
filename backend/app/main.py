"""FastAPI entry point. Business endpoints are added in subsequent TODO tasks."""

import uuid
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(title="지금이니? API", version="0.1.0")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


@app.get("/api/v1/health")
def health() -> JSONResponse:
    # 계약(api_contract 01절): 200 {status, server_time}. DB·키 등 내부 정보는 노출하지 않는다.
    now = utc_now_iso()
    request_id = f"req_{uuid.uuid4().hex}"
    return JSONResponse(
        content={
            "data": {"status": "ok", "server_time": now},
            "meta": {"request_id": request_id, "server_time": now},
        },
        headers={"X-Request-ID": request_id},
    )
