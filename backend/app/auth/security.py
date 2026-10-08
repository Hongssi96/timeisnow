"""Session issuance, CSRF, rate limits and current-member resolution.

Spring Security가 맡는 공통 인증 관심사. SQL은 repository에 위임한다.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import os
import secrets
from urllib.parse import urlsplit

from dotenv import dotenv_values

from app.auth import repository
from app.common.database import ROOT
from app.common.errors import AuthError


def settings():
    values = {**dotenv_values(ROOT / '.env'), **os.environ}
    env = values.get('AUTH_ENV', 'development')
    origin = values.get('AUTH_PUBLIC_ORIGIN', 'http://127.0.0.1:5173')
    secret = values.get('AUTH_RATE_LIMIT_SECRET', '')
    if not isinstance(origin, str) or not isinstance(secret, str):
        raise AuthError(503, 'SERVICE_UNAVAILABLE', '인증 설정을 확인할 수 없어요.')
    try:
        parsed = urlsplit(origin)
        parsed.port
    except ValueError:
        raise AuthError(503, 'SERVICE_UNAVAILABLE', '인증 설정을 확인할 수 없어요.') from None
    valid = (env in ('development', 'production') and len(secret) >= 32
             and parsed.path == '' and not parsed.query and not parsed.fragment
             and not parsed.username and not parsed.password and parsed.hostname)
    if env == 'production':
        valid = valid and parsed.scheme == 'https'
    else:
        valid = valid and parsed.scheme == 'http' and parsed.hostname in ('localhost', '127.0.0.1')
    if not valid:
        raise AuthError(503, 'SERVICE_UNAVAILABLE', '인증 설정을 확인할 수 없어요.')
    return origin, secret.encode(), env == 'production'


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def cookie_name(secure):
    return '__Host-timeisnow_session' if secure else 'timeisnow_dev_session'


def set_cookie(response, raw, secure, expires):
    response.set_cookie(cookie_name(secure), raw, expires=expires.astimezone(timezone.utc), httponly=True,
                        secure=secure, samesite='lax', path='/')


def session(connection, request, secure, required=False):
    raw = request.cookies.get(cookie_name(secure))
    if not raw or len(raw) > 128:
        if required:
            raise AuthError(401, 'AUTH_REQUIRED', '로그인이 필요해요.')
        return None
    row = repository.find_session(connection, digest(raw))
    now = datetime.now(timezone.utc)
    if not row or min(row['absolute_expires_at'], row['idle_expires_at']) <= now:
        if required:
            raise AuthError(401, 'SESSION_EXPIRED', '로그인이 만료됐어요.')
        return None
    if row['user_id'] and row['status'] != 'active':
        raise AuthError(401, 'AUTH_REQUIRED', '로그인이 필요해요.')
    if required and not row['user_id']:
        raise AuthError(401, 'AUTH_REQUIRED', '로그인이 필요해요.')
    return row


def require_csrf(connection, request, origin, secure):
    row = session(connection, request, secure)
    supplied = request.headers.get('x-csrf-token', '')
    allowed_origins = {origin}
    if not secure:
        # Only the two configured development loopback aliases at the same port.
        port = urlsplit(origin).port
        suffix = f':{port}' if port and port != 80 else ''
        allowed_origins = {f'http://localhost{suffix}', f'http://127.0.0.1{suffix}'}
    if (request.headers.get('origin') not in allowed_origins or not row or not supplied
            or not hmac.compare_digest(row['csrf_token_hash'], digest(supplied))):
        raise AuthError(403, 'CSRF_INVALID', '화면을 새로고침하고 다시 시도해주세요.')
    return row


def create_session(connection, user_id=None):
    raw, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    expiry = now + (timedelta(days=7) if user_id else timedelta(minutes=15))
    idle = min(expiry, now + timedelta(hours=24))
    repository.insert_session(connection, digest(raw), user_id, digest(csrf), expiry, idle)
    return raw, csrf, expiry


def bucket(connection, scope, value, seconds, maximum, secret):
    key = hmac.new(secret, (scope + ':' + value).encode(), hashlib.sha256).hexdigest()
    now = repository.clock_now(connection)
    start = int(now.timestamp()) // seconds * seconds
    expiry = datetime.fromtimestamp(start + seconds, timezone.utc)
    repository.ensure_bucket(connection, scope, key, start, expiry)
    row = repository.bucket_count(connection, scope, key, start)
    if row['count'] >= maximum:
        raise AuthError(429, 'RATE_LIMITED', '요청이 많아요. 잠시 후 다시 시도해주세요.',
                        {'Retry-After': str(max(1, int((expiry-now).total_seconds()) + 1))})
    return scope, key, start


def increment(connection, key):
    repository.increment_bucket(connection, key)


def authenticated(connection, request, write=False):
    origin, _, secure = settings()
    row = session(connection, request, secure, required=True)
    if write:
        require_csrf(connection, request, origin, secure)
    repository.extend_session(connection, row['token_hash'])
    return row['user_id']
