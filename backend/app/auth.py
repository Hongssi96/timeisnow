"""Small password/session authentication. Never log credentials or token values."""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import os
import re
import secrets
from urllib.parse import urlsplit
from uuid import uuid4

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from dotenv import dotenv_values
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response
from psycopg import Error as DatabaseError
from psycopg.errors import UniqueViolation
from psycopg.rows import dict_row
from pydantic import BaseModel, ConfigDict, field_validator

from app.database import ROOT, connect_db

router = APIRouter(prefix='/api/v1')
hasher = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)
dummy_hash = hasher.hash(secrets.token_urlsafe(32))


class AuthError(Exception):
    def __init__(self, status, code, message, headers=None):
        self.status, self.code, self.message, self.headers = status, code, message, headers


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


def iso(value):
    return value.isoformat(timespec='seconds').replace('+00:00', 'Z')


@contextmanager
def database():
    try:
        with connect_db() as connection:
            connection.row_factory = dict_row
            yield connection
    except DatabaseError:
        raise AuthError(503, 'SERVICE_UNAVAILABLE', '인증 서버에 연결할 수 없어요.') from None


def answer(request, data, status=200):
    return JSONResponse({'data': data, 'meta': {'request_id': request.state.request_id,
                        'server_time': iso(datetime.now(timezone.utc))}}, status_code=status,
                        headers={'Cache-Control': 'no-store'})


def cookie_name(secure):
    return '__Host-timeisnow_session' if secure else 'timeisnow_dev_session'


def session(connection, request, secure, required=False):
    raw = request.cookies.get(cookie_name(secure))
    if not raw or len(raw) > 128:
        if required:
            raise AuthError(401, 'AUTH_REQUIRED', '로그인이 필요해요.')
        return None
    row = connection.execute('''SELECT s.*, u.status FROM auth_sessions s
        LEFT JOIN users u ON u.id=s.user_id WHERE token_hash=%s FOR UPDATE OF s''',
        (digest(raw),)).fetchone()
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
    connection.execute('INSERT INTO auth_sessions VALUES(%s,%s,%s,%s,%s)',
                       (digest(raw), user_id, digest(csrf), expiry, idle))
    return raw, csrf, expiry


def set_cookie(response, raw, secure, expires):
    response.set_cookie(cookie_name(secure), raw, expires=expires.astimezone(timezone.utc), httponly=True,
                        secure=secure, samesite='lax', path='/')


def bucket(connection, scope, value, seconds, maximum, secret):
    key = hmac.new(secret, (scope + ':' + value).encode(), hashlib.sha256).hexdigest()
    now = connection.execute('SELECT clock_timestamp() AS now').fetchone()['now']
    start = int(now.timestamp()) // seconds * seconds
    expiry = datetime.fromtimestamp(start + seconds, timezone.utc)
    connection.execute('''INSERT INTO auth_rate_limit_buckets VALUES(%s,%s,%s,0,%s)
        ON CONFLICT DO NOTHING''', (scope, key, start, expiry))
    row = connection.execute('''SELECT count FROM auth_rate_limit_buckets
        WHERE scope=%s AND key_hash=%s AND window_start=%s FOR UPDATE''', (scope, key, start)).fetchone()
    if row['count'] >= maximum:
        raise AuthError(429, 'RATE_LIMITED', '요청이 많아요. 잠시 후 다시 시도해주세요.',
                        {'Retry-After': str(max(1, int((expiry-now).total_seconds()) + 1))})
    return scope, key, start


def increment(connection, key):
    connection.execute('''UPDATE auth_rate_limit_buckets SET count=count+1
        WHERE scope=%s AND key_hash=%s AND window_start=%s''', key)


class LoginInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    email: str
    password: str

    @field_validator('email')
    @classmethod
    def email_format(cls, value):
        value = value.strip().lower()
        if len(value) > 254 or not re.fullmatch(r"[a-z0-9!#$%&'*+/=?^_`{|}~.-]+@[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?\.[a-z]{2,63}", value):
            raise ValueError('Invalid email')
        local, domain = value.rsplit('@', 1)
        if len(local) > 64 or local.startswith('.') or local.endswith('.') or '..' in value or any(not label or len(label)>63 or label.startswith('-') or label.endswith('-') for label in domain.split('.')):
            raise ValueError('Invalid email')
        return value

    @field_validator('password')
    @classmethod
    def password_length(cls, value):
        if not 15 <= len(value) <= 128:
            raise ValueError('Invalid password')
        return value


class RegisterInput(LoginInput):
    display_name: str

    @field_validator('display_name')
    @classmethod
    def name_length(cls, value):
        value = value.strip()
        if not 1 <= len(value) <= 30:
            raise ValueError('Invalid name')
        return value

    @field_validator('password')
    @classmethod
    def weak_password(cls, value):
        if value.lower() in {'123456789012345', '1234567890123456', 'passwordpassword', 'qwertyuiopasdfgh', 'aaaaaaaaaaaaaaa'}:
            raise ValueError('Weak password')
        return value


class EmptyInput(BaseModel):
    model_config = ConfigDict(extra='forbid')


@router.get('/auth/csrf')
def csrf(request: Request):
    _, _, secure = settings()
    with database() as connection:
        connection.execute('DELETE FROM auth_sessions WHERE idle_expires_at <= now() OR absolute_expires_at <= now()')
        connection.execute('DELETE FROM auth_rate_limit_buckets WHERE expires_at <= now()')
        row = session(connection, request, secure)
        if row:
            raw = request.cookies[cookie_name(secure)]
            token = secrets.token_urlsafe(32)
            expiry = row['absolute_expires_at']
            connection.execute('UPDATE auth_sessions SET csrf_token_hash=%s WHERE token_hash=%s',
                               (digest(token), row['token_hash']))
        else:
            raw, token, expiry = create_session(connection)
    response = answer(request, {'csrf_token': token, 'expires_at': iso(expiry)})
    set_cookie(response, raw, secure, expiry)
    return response


@router.post('/auth/register')
def register(request: Request, body: RegisterInput):
    origin, secret, secure = settings()
    conflict = False
    user_id = uuid4()
    with database() as connection:
        require_csrf(connection, request, origin, secure)
        increment(connection, bucket(connection, 'register-ip', request.client.host, 3600, 5, secret))
        try:
            with connection.transaction():
                connection.execute('INSERT INTO users(id,display_name) VALUES(%s,%s)', (user_id, body.display_name))
                connection.execute('INSERT INTO auth_credentials VALUES(%s,%s,%s)',
                                   (user_id, body.email, hasher.hash(body.password)))
                connection.execute('INSERT INTO user_profiles(user_id) VALUES(%s)', (user_id,))
        except UniqueViolation:
            conflict = True
    if conflict:
        raise AuthError(409, 'EMAIL_UNAVAILABLE', '이미 가입된 이메일이에요. 로그인해주세요.')
    return answer(request, {'user_id': str(user_id)}, 201)


@router.post('/auth/login')
def login(request: Request, body: LoginInput):
    origin, secret, secure = settings()
    invalid = False
    with database() as connection:
        old = require_csrf(connection, request, origin, secure)
        increment(connection, bucket(connection, 'login-ip', request.client.host, 900, 30, secret))
        email_key = bucket(connection, 'login-email', body.email, 900, 5, secret)
        user = connection.execute('''SELECT c.*,u.status FROM auth_credentials c
            JOIN users u ON u.id=c.user_id WHERE email_normalized=%s''', (body.email,)).fetchone()
        try:
            hasher.verify(user['password_hash'] if user else dummy_hash, body.password)
        except VerifyMismatchError:
            invalid = True
        invalid = invalid or not user or user['status'] != 'active'
        if invalid:
            increment(connection, email_key)
        else:
            connection.execute('DELETE FROM auth_sessions WHERE token_hash=%s', (old['token_hash'],))
            raw, token, expiry = create_session(connection, user['user_id'])
    if invalid:
        raise AuthError(401, 'INVALID_CREDENTIALS', '이메일 또는 비밀번호를 확인해주세요.')
    response = answer(request, {'user_id': str(user['user_id']), 'session_expires_at': iso(expiry), 'csrf_token': token})
    set_cookie(response, raw, secure, expiry)
    return response


@router.get('/me')
def me(request: Request):
    _, _, secure = settings()
    with database() as connection:
        row = session(connection, request, secure, required=True)
        user = connection.execute('SELECT display_name FROM users WHERE id=%s', (row['user_id'],)).fetchone()
        profile = connection.execute('SELECT * FROM user_profiles WHERE user_id=%s', (row['user_id'],)).fetchone()
        profile.pop('user_id')
        connection.execute('''UPDATE auth_sessions SET idle_expires_at=LEAST(absolute_expires_at,now()+interval '24 hours')
            WHERE token_hash=%s''', (row['token_hash'],))
    return answer(request, {'user_id': str(row['user_id']), 'display_name': user['display_name'], 'profile': profile})


@router.post('/auth/logout')
def logout(request: Request, body: EmptyInput):
    origin, _, secure = settings()
    with database() as connection:
        row = require_csrf(connection, request, origin, secure)
        connection.execute('DELETE FROM auth_sessions WHERE token_hash=%s', (row['token_hash'],))
    response = Response(status_code=204, headers={'Cache-Control': 'no-store'})
    response.delete_cookie(cookie_name(secure), path='/', httponly=True, secure=secure, samesite='lax')
    return response
