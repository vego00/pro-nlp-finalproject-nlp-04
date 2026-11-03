---
title: "src/storage/database.py"
tags:
  - code
  - layer/postgres
---

# `src/storage/database.py`

- **소속 계층 태그**: `#layer/postgres`
- **상위 아키텍처 노트**: [[00-Index]], [[02-Storage-and-Auth]], [[storage-auth-flow.canvas]]
- **내부 모듈 의존성(Imports)**: [[mod__config__config]]

> Shared asynchronous database lifecycle and relational schema.

## 정의된 클래스 / 상태 스키마
- 없음

## 정의된 함수 / 노드
- `def get_engine()`

## 소스 코드 미리보기 (`src/storage/database.py`)

```python
"""Shared asynchronous database lifecycle and relational schema."""
from sqlalchemy import Column, MetaData, Table, String, Text, Integer, ForeignKey, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import create_async_engine
from config import config

metadata = MetaData()
users = Table('users', metadata, Column('id', String, primary_key=True), Column('key', String, unique=True, nullable=False))
documents = Table('documents', metadata,
    Column('id', String, primary_key=True), Column('owner_id', ForeignKey('users.id'), nullable=False),
    Column('title', Text, nullable=False), Column('draft', Text, nullable=False), Column('draft_document', JSONB),
    Column('draft_revision', Integer, nullable=False, default=0),
    Column('created_at', DateTime(timezone=True), server_default=func.now(), nullable=False),
    Column('updated_at', DateTime(timezone=True), server_default=func.now(), nullable=False, index=True))
sessions = Table('sessions', metadata,
    Column('id', String, primary_key=True), Column('document_id', ForeignKey('documents.id'), unique=True, nullable=False),
    Column('state', JSONB, nullable=False), Column('state_schema_version', Integer, nullable=False, default=1),
    Column('markdown', Text, nullable=False), Column('status', String, nullable=False), Column('error', Text),
    Column('run_token', String))
engine = None


def get_engine():
    global engine
    if engine is None:
        url = config.DATABASE_URL
        if not url:
            raise RuntimeError('DATABASE_URL 설정이 필요합니다.')
        if url.startswith('postgresql://'):
            url = url.replace('postgresql://', 'postgresql+psycopg://', 1)
        engine = create_async_engine(url, pool_pre_ping=True)
    return engine
```
