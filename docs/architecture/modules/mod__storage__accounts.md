---
title: "src/storage/accounts.py"
tags:
  - code
  - layer/postgres
---

# `src/storage/accounts.py`

- **소속 계층 태그**: `#layer/postgres`
- **상위 아키텍처 노트**: [[00-Index]], [[02-Storage-and-Auth]], [[storage-auth-flow.canvas]]
- **내부 모듈 의존성(Imports)**: [[mod__storage__database]]

> Provision accounts: PYTHONPATH=src python -m storage.accounts EMAIL [flags].

## 정의된 클래스 / 상태 스키마
- 없음

## 정의된 함수 / 노드
- `def normalize_email(email)`
- `def validate_password(password)`
- `async def adopt_local(conn, user_id)`
- `async def sync_admin_from_env(email, password)`
- `async def main()`

## 소스 코드 미리보기 (`src/storage/accounts.py`)

```python
"""Provision accounts: PYTHONPATH=src python -m storage.accounts EMAIL [flags].

The initial administrator is normally managed through ADMIN_EMAIL/ADMIN_PASSWORD
in .env and synchronised on every server start (see sync_admin_from_env).
"""
import argparse
import asyncio
from getpass import getpass
import logging
from uuid import uuid4
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from sqlalchemy import text
from storage.database import get_engine

LOCAL_OWNER = '00000000-0000-0000-0000-000000000001'
MIN_PASSWORD_LENGTH = 4
logger = logging.getLogger(__name__)


def normalize_email(email):
    email = (email or '').strip().lower()
    if '@' not in email or len(email) > 254:
        raise ValueError('올바른 이메일을 입력하세요.')
    return email


def validate_password(password):
    if len(password) < MIN_PASSWORD_LENGTH or len(password) > 1024:
        raise ValueError(f'비밀번호는 {MIN_PASSWORD_LENGTH}자 이상 1024자 이하여야 합니다.')


async def adopt_local(conn, user_id):
    """Hand documents/jobs owned by the legacy local user over to user_id."""
    await conn.execute(text('UPDATE documents SET owner_id=:id WHERE owner_id=:local'), {'id': user_id, 'local': LOCAL_OWNER})
    await conn.execute(text('UPDATE jobs SET owner_id=:id WHERE owner_id=:local'), {'id': user_id, 'local': LOCAL_OWNER})


async def sync_admin_from_env(email, password):
    """Ensure the .env administrator exists and matches ADMIN_PASSWORD.

    Returns 'skipped', 'created', 'updated' or 'unchanged'.
    - created: new admin; legacy local documents are adopted once.
    - updated: password changed in .env (existing login sessions are revoked)
      or the account had been demoted/deactivated.
    Changing ADMIN_EMAIL creates a new admin; the previous account is kept.
    """
    email, password = (email or '').strip(), password or ''
    if not email and not password:
        return 'skipped'
    if not email or not password:
        raise RuntimeError('.env의 ADMIN_EMAIL과 ADMIN_PASSWORD는 함께 설정해야 합니다.')
    email = normalize_email(email)
    validate_password(password)
    hasher = PasswordHasher()
    async with get_engine().begin() as c:
        row = (await c.execute(text('SELECT id,password_hash,is_admin,active FROM users WHERE email=:email FOR UPDATE'), {'email': email})).mappings().first()
        if row is None:
            uid = str(uuid4())
            password_hash = await asyncio.to_thread(hasher.hash, password)
            await c.execute(text('INSERT INTO users(id,key,email,password_hash,is_admin,allow_google) VALUES (:id,:key,:email,:hash,true,false)'), {'id': uid, 'key': 'account:'+uid, 'email': email, 'hash': password_hash})
            await adopt_local(c, uid)
            logger.info('관리자 계정 생성: %s', email)
            return 'created'
        try:
            same = bool(row['password_hash']) and await asyncio.to_thread(hasher.verify, row['password_hash'], password)
        except (VerificationError, InvalidHashError):
            same = False
        if same and row['is_admin'] and row['active']:
            return 'unchanged'
        params = {'id': row['id']}
        assignments = 'is_admin=true, active=true'
        if not same:
            params['hash'] = await asyncio.to_thread(hasher.hash, password)
            assignments += ', password_hash=:hash'
            await c.execute(text('DELETE FROM login_sessions WHERE user_id=:id'), {'id': row['id']})
        await c.execute(text(f'UPDATE users SET {assignments} WHERE id=:id'), params)
        logger.info('관리자 계정 갱신: %s', email)
        return 'updated'


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('email')
    parser.add_argument('--admin', action='store_true')
    parser.add_argument('--allow-google', action='store_true')
    parser.add_argument('--google-only', action='store_true')
    parser.add_argument('--adopt-local', action='store_true', help='Explicitly take ownership of existing local documents')
    args = parser.parse_args()
    email = normalize_email(args.email)
```
