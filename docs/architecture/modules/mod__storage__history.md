---
title: "src/storage/history.py"
tags:
  - code
  - layer/postgres
---

# `src/storage/history.py`

- **소속 계층 태그**: `#layer/postgres`
- **상위 아키텍처 노트**: [[00-Index]], [[02-Storage-and-Auth]], [[storage-auth-flow.canvas]]
- **내부 모듈 의존성(Imports)**: [[mod__storage__database]]

> History and durable execution records; callers supply authenticated ownership.

## 정의된 클래스 / 상태 스키마
- 없음

## 정의된 함수 / 노드
- `def input_digest(sid, kind, payload)`
- `async def append_version(connection, did, kind, markdown, document, revision, reason)`
- `async def versions(did, limit, offset)`
- `async def version(did, version_id)`
- `async def existing_job(owner, key, sid, kind, payload)`
- `async def job_list(owner, sid, limit, offset)`
- `async def get_job(owner, job_id)`

## 소스 코드 미리보기 (`src/storage/history.py`)

```python
"""History and durable execution records; callers supply authenticated ownership."""
import hashlib
import json
from uuid import uuid4
from sqlalchemy import text
from fastapi import HTTPException
from storage.database import get_engine


def input_digest(sid, kind, payload):
    raw = json.dumps([sid, kind, payload], sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    return hashlib.sha256(raw.encode()).hexdigest()


async def append_version(connection, did, kind, markdown, document=None, revision=None, reason='save'):
    # Every writer holds the document row lock, including generation and restore.
    await connection.execute(text('SELECT id FROM documents WHERE id=:id FOR UPDATE'), {'id': did})
    if revision is None:
        revision = (await connection.execute(text('SELECT COALESCE(MAX(revision),-1)+1 FROM document_versions WHERE document_id=:id AND kind=:kind'), {'id': did, 'kind': kind})).scalar_one()
    await connection.execute(text('INSERT INTO document_versions(document_id,kind,revision,markdown,document,reason) VALUES (:id,:kind,:revision,:markdown,CAST(:document AS jsonb),:reason)'), {'id': did, 'kind': kind, 'revision': revision, 'markdown': markdown, 'document': json.dumps(document), 'reason': reason})


async def versions(did, limit=20, offset=0):
    async with get_engine().connect() as c:
        rows = await c.execute(text('SELECT id,revision,kind,reason,created_at FROM document_versions WHERE document_id=:id ORDER BY id DESC LIMIT :limit OFFSET :offset'), {'id': did, 'limit': limit, 'offset': offset})
        return [dict(row) for row in rows.mappings()]


async def version(did, version_id):
    async with get_engine().connect() as c:
        row = (await c.execute(text('SELECT * FROM document_versions WHERE document_id=:did AND id=:id'), {'did': did, 'id': version_id})).mappings().first()
    if row is None:
        raise HTTPException(404, '문서 버전이 없습니다.')
    return dict(row)


async def existing_job(owner, key, sid, kind, payload):
    async with get_engine().connect() as c:
        row = (await c.execute(text('SELECT * FROM jobs WHERE owner_id=:owner AND request_key=:key'), {'owner': owner, 'key': key})).mappings().first()
    if row is not None and row['input_hash'] != input_digest(sid, kind, payload):
        raise HTTPException(409, '같은 요청 키에 다른 입력을 사용할 수 없습니다.')
    return dict(row) if row else None


async def job_list(owner, sid, limit=20, offset=0):
    async with get_engine().connect() as c:
        rows = await c.execute(text('SELECT id,kind,status,error,created_at,finished_at,base_revision FROM jobs WHERE owner_id=:owner AND session_id=:sid ORDER BY created_at DESC,id LIMIT :limit OFFSET :offset'), {'owner': owner, 'sid': sid, 'limit': limit, 'offset': offset})
        return [dict(row) for row in rows.mappings()]


async def get_job(owner, job_id):
    async with get_engine().connect() as c:
        row = (await c.execute(text('SELECT id,session_id,kind,status,result,error,created_at,finished_at FROM jobs WHERE owner_id=:owner AND id=:id'), {'owner': owner, 'id': job_id})).mappings().first()
    if not row:
        raise HTTPException(404, '실행 기록이 없습니다.')
    return dict(row)
```
