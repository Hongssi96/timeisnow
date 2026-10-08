"""Uniform {data, meta} response envelope for successful endpoints."""
from datetime import datetime, timezone

from fastapi.responses import JSONResponse

from app.common.timeutil import iso


def answer(request, data, status=200):
    return JSONResponse({'data': data, 'meta': {'request_id': request.state.request_id,
                        'server_time': iso(datetime.now(timezone.utc))}}, status_code=status,
                        headers={'Cache-Control': 'no-store'})
