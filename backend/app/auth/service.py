"""Signup, login, session refresh and logout business flows."""
import secrets
from uuid import uuid4

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from psycopg.errors import UniqueViolation

from app.auth import repository, security
from app.common.database import database
from app.common.errors import AuthError
from app.common.timeutil import iso

hasher = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)
dummy_hash = hasher.hash(secrets.token_urlsafe(32))


def csrf(request, secure):
    with database() as connection:
        repository.delete_expired_sessions(connection)
        repository.delete_expired_buckets(connection)
        row = security.session(connection, request, secure)
        if row:
            raw = request.cookies[security.cookie_name(secure)]
            token = secrets.token_urlsafe(32)
            expiry = row['absolute_expires_at']
            repository.update_session_csrf(connection, row['token_hash'], security.digest(token))
        else:
            raw, token, expiry = security.create_session(connection)
    return raw, token, expiry


def register(request, body):
    origin, secret, secure = security.settings()
    conflict = False
    user_id = uuid4()
    with database() as connection:
        security.require_csrf(connection, request, origin, secure)
        security.increment(connection, security.bucket(connection, 'register-ip', request.client.host, 3600, 5, secret))
        try:
            with connection.transaction():
                repository.insert_user(connection, user_id, body.display_name)
                repository.insert_credential(connection, user_id, body.email, hasher.hash(body.password))
                repository.insert_profile(connection, user_id)
        except UniqueViolation:
            conflict = True
    if conflict:
        raise AuthError(409, 'EMAIL_UNAVAILABLE', '이미 가입된 이메일이에요. 로그인해주세요.')
    return user_id


def login(request, body):
    origin, secret, secure = security.settings()
    invalid = False
    with database() as connection:
        old = security.require_csrf(connection, request, origin, secure)
        security.increment(connection, security.bucket(connection, 'login-ip', request.client.host, 900, 30, secret))
        email_key = security.bucket(connection, 'login-email', body.email, 900, 5, secret)
        user = repository.find_credential(connection, body.email)
        try:
            hasher.verify(user['password_hash'] if user else dummy_hash, body.password)
        except VerifyMismatchError:
            invalid = True
        invalid = invalid or not user or user['status'] != 'active'
        if invalid:
            security.increment(connection, email_key)
        else:
            repository.delete_session(connection, old['token_hash'])
            raw, token, expiry = security.create_session(connection, user['user_id'])
    if invalid:
        raise AuthError(401, 'INVALID_CREDENTIALS', '이메일 또는 비밀번호를 확인해주세요.')
    return {'user_id': str(user['user_id']), 'session_expires_at': iso(expiry), 'csrf_token': token}, raw, expiry


def me(request, secure):
    with database() as connection:
        row = security.session(connection, request, secure, required=True)
        from app.retention.service import sweep
        sweep(connection,row['user_id'])
        user = repository.find_display_name(connection, row['user_id'])
        profile = repository.find_profile(connection, row['user_id'])
        profile.pop('user_id')
        repository.extend_session(connection, row['token_hash'])
    return {'user_id': str(row['user_id']), 'display_name': user['display_name'], 'profile': profile}


def logout(request, origin, secure):
    with database() as connection:
        row = security.require_csrf(connection, request, origin, secure)
        repository.delete_session(connection, row['token_hash'])
