"""Administrator-provisioned password/Google accounts with server-side sessions."""
import asyncio
from collections import defaultdict, deque
from contextvars import ContextVar
from datetime import datetime, timedelta, timezone
import hashlib
import secrets
import time

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import text
from config import config as settings
from storage.database import get_engine

router = APIRouter(prefix='/api/auth')
current_user = ContextVar('current_user', default=None)
hasher = PasswordHasher()
attempts = defaultdict(deque)
oauth = OAuth()
oauth.register(name='google', client_id=settings.GOOGLE_CLIENT_ID, client_secret=settings.GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile', 'code_challenge_method': 'S256'})


def owner_id():
    user = current_user.get()
    if not user:
        raise HTTPException(401, '로그인이 필요합니다.')
    return user['id']


def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


async def identify(request):
    token = request.cookies.get('div_login')
    if not token:
        return None
    async with get_engine().connect() as c:
        row = (await c.execute(text('SELECT u.id,u.email,u.is_admin,l.csrf FROM login_sessions l JOIN users u ON u.id=l.user_id WHERE l.token_hash=:token AND l.expires_at>now() AND u.active'), {'token': digest(token)})).mappings().first()
    return dict(row) if row else None


async def issue_login(user_id):
    token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    async with get_engine().begin() as c:
        await c.execute(text('INSERT INTO login_sessions(token_hash,user_id,csrf,expires_at) VALUES (:token,:uid,:csrf,:expires)'), {'token': digest(token), 'uid': user_id, 'csrf': csrf, 'expires': datetime.now(timezone.utc)+timedelta(hours=12)})
    return token


def set_login(response, token):
    response.set_cookie('div_login', token, httponly=True, secure=settings.AUTH_COOKIE_SECURE, samesite='lax', max_age=43200, path='/')
    return response


def check_origin(request):
    origin = request.headers.get('origin')
    if origin and origin != settings.APP_BASE_URL:
        raise HTTPException(403, '허용되지 않은 요청 출처입니다.')
    if request.headers.get('x-requested-with') != 'DIV':
        raise HTTPException(403, '요청 확인 헤더가 필요합니다.')


class Credentials(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=1024)


@router.post('/login')
async def login(request: Request, body: Credentials):
    check_origin(request)
    key = request.client.host if request.client else 'unknown'
    now = time.monotonic()
    queue = attempts[key]
    while queue and queue[0] < now-60:
        queue.popleft()
    if len(queue) >= 5:
        raise HTTPException(429, '잠시 후 다시 로그인하세요.')
    queue.append(now)
    async with get_engine().connect() as c:
        user = (await c.execute(text('SELECT * FROM users WHERE email=:email AND active'), {'email': body.email.strip().lower()})).mappings().first()
    stored = user['password_hash'] if user and user['password_hash'] else DUMMY_HASH
    try:
        valid = await asyncio.to_thread(hasher.verify, stored, body.password)
    except (VerificationError, InvalidHashError):
        valid = False
    if not valid or not user or not user['password_hash']:
        raise HTTPException(401, '이메일 또는 비밀번호를 확인하세요.')
    return set_login(JSONResponse({'ok': True}), await issue_login(user['id']))


DUMMY_HASH = hasher.hash(secrets.token_urlsafe(32))


@router.get('/me')
async def me(request: Request):
    user = await identify(request)
    if not user:
        raise HTTPException(401, '로그인이 필요합니다.')
    return user


@router.get('/options')
def options():
    return {'google': bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)}


@router.post('/logout')
async def logout(request: Request):
    check_origin(request)
    user = await identify(request)
    if not user or not secrets.compare_digest(request.headers.get('x-csrf-token', ''), user['csrf']):
        raise HTTPException(403, '요청을 확인할 수 없습니다.')
    async with get_engine().begin() as c:
        await c.execute(text('DELETE FROM login_sessions WHERE token_hash=:token'), {'token': digest(request.cookies['div_login'])})
    response = JSONResponse({'ok': True})
    response.delete_cookie('div_login', path='/')
    request.session.clear()
    return response


@router.get('/google')
async def google_login(request: Request):
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(503, 'Google 로그인이 설정되지 않았습니다.')
    return await oauth.google.authorize_redirect(request, settings.APP_BASE_URL + '/api/auth/google/callback', prompt='select_account')


@router.get('/google/callback')
async def google_callback(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
        info = token.get('userinfo')
        if not info or info.get('email_verified') is not True or not info.get('sub'):
            raise ValueError('unverified identity')
        async with get_engine().begin() as c:
            user = (await c.execute(text("SELECT u.* FROM external_identities i JOIN users u ON u.id=i.user_id WHERE i.provider='google' AND i.subject=:sub AND u.active AND u.allow_google"), {'sub': info['sub']})).mappings().first()
            if not user:
                # Only accounts explicitly enabled for Google by an administrator can link.
                user = (await c.execute(text('SELECT * FROM users WHERE email=:email AND active AND allow_google FOR UPDATE'), {'email': info['email'].lower()})).mappings().first()
                if not user:
                    raise ValueError('account not provisioned')
                linked = (await c.execute(text("SELECT subject FROM external_identities WHERE provider='google' AND user_id=:uid"), {'uid': user['id']})).first()
                if linked:
                    raise ValueError('different identity already linked')
                await c.execute(text("INSERT INTO external_identities(provider,subject,user_id) VALUES ('google',:sub,:uid)"), {'sub': info['sub'], 'uid': user['id']})
        response = RedirectResponse('/', status_code=303)
        return set_login(response, await issue_login(user['id']))
    except Exception:
        # Never send provider tokens or authorization codes to logs or responses.
        raise HTTPException(401, 'Google 로그인에 실패했습니다. 관리자에게 계정 등록을 확인하세요.') from None
