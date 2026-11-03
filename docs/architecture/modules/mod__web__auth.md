---
title: "src/web/auth.py"
tags:
  - code
  - layer/web
---

# `src/web/auth.py`

- **소속 계층 태그**: `#layer/web`
- **상위 아키텍처 노트**: [[00-Index]], [[01-Web-and-Editor]]
- **내부 모듈 의존성(Imports)**: [[mod__config__config]], [[mod__storage__database]]

> Administrator-provisioned password/Google accounts with server-side sessions.

## 정의된 클래스 / 상태 스키마
- `Credentials`

## 정의된 함수 / 노드
- `def owner_id()`
- `def digest(token)`
- `async def identify(request)`
- `async def issue_login(user_id)`
- `def set_login(response, token)`
- `def check_origin(request)`
- `async def login(request, body)`
- `async def me(request)`
- `def options()`
- `async def logout(request)`
- `async def google_login(request)`
- `async def google_callback(request)`

## 소스 코드 미리보기 (`src/web/auth.py`)

```python
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
```
