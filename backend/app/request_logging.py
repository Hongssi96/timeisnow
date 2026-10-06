"""Allowlisted request metadata only; never format exception messages or payloads."""
from datetime import datetime, timezone
import json
import logging
import math
import os
from pathlib import Path
import re
import sys
from time import perf_counter

from dotenv import dotenv_values

LOGGER_NAME = 'timeisnow.requests'
EVENTS = {'http.request.completed', 'http.request.failed'}
METHODS = {'GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS', 'TRACE', 'CONNECT'}


class RequestJsonFormatter(logging.Formatter):
    def format(self, record):
        # Ignore msg, args, exc_info and all unrelated extra fields.
        data = {
            'timestamp': datetime.fromtimestamp(record.created, timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z'),
            'level': record.levelname, 'service': 'backend', 'event': record.event,
        }
        for field in ('request_id', 'method', 'route', 'status_code', 'duration_ms', 'error_code', 'exception_type'):
            if hasattr(record, field):
                data[field] = getattr(record, field)
        return json.dumps(data, ensure_ascii=False, allow_nan=False)


class RequestEventFilter(logging.Filter):
    def filter(self, record):
        return getattr(record, 'event', None) in EVENTS


def configure_request_logger(level=None):
    if level is None:
        configured = dotenv_values(Path(__file__).resolve().parents[2] / '.env').get('LOG_LEVEL', 'INFO')
        level = os.environ.get('LOG_LEVEL', configured)
    level = level if level in ('INFO', 'WARNING', 'ERROR') else 'INFO'
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)
    logger.propagate = False
    logger.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(RequestJsonFormatter())
    handler.addFilter(RequestEventFilter())
    logger.addHandler(handler)
    return logger


logger = configure_request_logger()


def record_request(request, status, started_at, exception=None):
    route = getattr(request.scope.get('route'), 'path', None)
    elapsed = (perf_counter() - started_at) * 1000
    fields = {
        'request_id': request.state.request_id,
        'method': request.method if request.method in METHODS else 'OTHER',
        'route': route if isinstance(route, str) else 'unmatched',
        'status_code': status,
        'duration_ms': round(max(0, elapsed), 2) if math.isfinite(elapsed) else 0,
    }
    code = getattr(request.state, 'error_code', None)
    if isinstance(code, str) and re.fullmatch(r'[A-Z][A-Z0-9_]{0,63}', code):
        fields['error_code'] = code
    if exception is not None:
        kind = type(exception).__name__
        error_fields = {**fields, 'event': 'http.request.failed',
                        'exception_type': kind if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,63}', kind) else 'Exception'}
        logger.error('', extra=error_fields)
    logger.info('', extra={**fields, 'event': 'http.request.completed'})
