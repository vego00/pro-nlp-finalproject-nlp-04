---
title: "src/storage/repository.py"
tags:
  - code
  - layer/postgres
---

# `src/storage/repository.py`

- **소속 계층 태그**: `#layer/postgres`
- **상위 아키텍처 노트**: [[00-Index]], [[02-Storage-and-Auth]], [[storage-auth-flow.canvas]]
- **내부 모듈 의존성(Imports)**: [[mod__storage__database]], [[mod__storage__history]], [[mod__web__auth]]

> Transactional session operations. Never hold a connection during model calls.

## 정의된 클래스 / 상태 스키마
- 없음

## 정의된 함수 / 노드
- `def encode(state)`
- `def decode(state)`
- `def title(markdown)`
- `async def ensure_owner()`
- `async def initialize()`
- `async def create(state, markdown, document, session_id)`
- `async def get(sid)`
- `async def listing(limit, offset)`
- `async def save(sid, markdown, document, revision, reason)`
- `async def claim(sid, expected_state, key, kind, payload, base_revision, resolved_input)`
- `async def checkpoint(session, token, markdown, status, error, job_result)`

## 소스 코드 미리보기 (`src/storage/repository.py`)

```python
"""Transactional session operations. Never hold a connection during model calls."""
from uuid import uuid4
from sqlalchemy import select, update, insert, func, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from langchain_core.messages import messages_to_dict, messages_from_dict
from fastapi import HTTPException
from storage.database import get_engine, users, documents as d, sessions as s
from web.auth import owner_id
from storage import history
import json

OWNER = '00000000-0000-0000-0000-000000000001'


def encode(state):
    return {**state, 'messages': messages_to_dict(state.get('messages', []))}


def decode(state):
    return {**state, 'messages': messages_from_dict(state.get('messages', []))}


def title(markdown):
    return next((line.strip().lstrip('#').strip()[:80] for line in markdown.splitlines() if line.strip()), '새 문서')


async def ensure_owner():
    async with get_engine().begin() as c:
        await c.execute(pg_insert(users).values(id=OWNER, key="local").on_conflict_do_nothing())


async def initialize():
    async with get_engine().begin() as c:
        version = (await c.execute(text('SELECT version_num FROM alembic_version'))).scalar_one()
        if version != '002_history_auth':
            raise RuntimeError('alembic upgrade head 실행이 필요합니다.')
        await c.execute(pg_insert(users).values(id=OWNER, key='local').on_conflict_do_nothing())
        await c.execute(text("UPDATE jobs SET status='interrupted',error='서버 재시작으로 중단되었습니다.',finished_at=now() WHERE status='running'"))
        await c.execute(text("UPDATE agent_runs SET status='interrupted',error='서버 재시작으로 중단되었습니다.',finished_at=now() WHERE status='running'"))
        await c.execute(update(s).where(s.c.status == 'running').values(status='error', error='서버 재시작으로 작업이 중단되었습니다. 다시 요청하세요.', run_token=None))


async def create(state, markdown='', document=None, session_id=None):
    sid, did = session_id or uuid4().hex, str(uuid4())
    async with get_engine().begin() as c:
        await c.execute(insert(d).values(id=did, owner_id=owner_id(), title=title(markdown), draft=markdown, draft_document=document, draft_revision=0))
        await history.append_version(c, did, 'draft', markdown, document, 0, 'create')
        await c.execute(insert(s).values(id=sid, document_id=did, state=encode(state), state_schema_version=1, markdown='', status='ready'))
    return await get(sid)


async def get(sid):
    async with get_engine().connect() as c:
        row = (await c.execute(select(s, d.c.title, d.c.draft, d.c.draft_document, d.c.draft_revision, d.c.updated_at).join(d).where(s.c.id == sid, d.c.owner_id == owner_id()))).mappings().first()
    if row is None:
        raise HTTPException(404, '세션이 없습니다. 새 문서를 시작하세요.')
    result = dict(row)
    if result['state_schema_version'] != 1:
        raise HTTPException(503, '지원하지 않는 저장 상태 버전입니다.')
    result['state'] = decode(result['state'])
    return result


async def listing(limit, offset):
    async with get_engine().connect() as c:
        rows = await c.execute(select(s.c.id, d.c.title, s.c.status, d.c.updated_at).join(d).where(d.c.owner_id == owner_id()).order_by(d.c.updated_at.desc(), s.c.id).limit(limit).offset(offset))
        return [dict(row) for row in rows.mappings()]


async def save(sid, markdown, document, revision, reason="save"):
    session = await get(sid)
    async with get_engine().begin() as c:
        result = await c.execute(update(d).where(d.c.id == session['document_id'], d.c.owner_id == owner_id(), d.c.draft_revision == revision).values(draft=markdown, draft_document=document, draft_revision=revision + 1, title=title(markdown), updated_at=func.now()).returning(d.c.title, d.c.draft, d.c.draft_document, d.c.draft_revision, d.c.updated_at))
        saved = result.mappings().first()
        if saved is None:
            raise HTTPException(409, '다른 곳에서 수정된 문서입니다. 최신본을 열거나 사본으로 저장하세요.')
        await history.append_version(c, session['document_id'], 'draft', markdown, document, revision+1, reason)
        session.update(saved)
    return session


async def claim(sid, expected_state, key, kind, payload, base_revision=None, resolved_input=None):
    session = await get(sid)
    owner = owner_id()
    base_revision = session["draft_revision"] if base_revision is None else base_revision
    token = uuid4().hex
    async with get_engine().begin() as c:
        await c.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:key,0))'), {'key': owner+':'+key})
        prior = (await c.execute(text('SELECT id,input_hash FROM jobs WHERE owner_id=:owner AND request_key=:key'), {'owner': owner, 'key': key})).mappings().first()
        hashed = history.input_digest(sid, kind, payload)
```
