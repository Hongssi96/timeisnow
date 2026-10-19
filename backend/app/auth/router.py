"""Auth endpoints; flows live in service, envelope/cookies assembled here."""
from fastapi import APIRouter, Request
from fastapi.responses import Response

from app.auth import security, service, profile_service
from app.auth.dto import EmptyInput, LoginInput, RegisterInput, ProfileInput
from app.auth.security import set_cookie, settings
from app.common.response import answer
from app.common.timeutil import iso

router = APIRouter(prefix='/api/v1')


@router.get('/auth/csrf')
def csrf(request: Request):
    _, _, secure = settings()
    raw, token, expiry = service.csrf(request, secure)
    response = answer(request, {'csrf_token': token, 'expires_at': iso(expiry)})
    set_cookie(response, raw, secure, expiry)
    return response


@router.post('/auth/register')
def register(request: Request, body: RegisterInput):
    user_id = service.register(request, body)
    return answer(request, {'user_id': str(user_id)}, 201)


@router.post('/auth/login')
def login(request: Request, body: LoginInput):
    data, raw, expiry = service.login(request, body)
    _, _, secure = settings()
    response = answer(request, data)
    set_cookie(response, raw, secure, expiry)
    return response


@router.get('/me')
def me(request: Request):
    _, _, secure = settings()
    return answer(request, service.me(request, secure))


@router.post('/auth/logout')
def logout(request: Request, body: EmptyInput):
    origin, _, secure = settings()
    service.logout(request, origin, secure)
    response = Response(status_code=204, headers={'Cache-Control': 'no-store'})
    response.delete_cookie(security.cookie_name(secure), path='/', httponly=True, secure=secure, samesite='lax')
    return response


@router.patch('/me/profile')
def profile(request: Request, body: ProfileInput):
    return answer(request,profile_service.update(request,body))
