---
title: "migrations/env.py"
tags:
  - code
  - layer/postgres
---

# `migrations/env.py`

- **소속 계층 태그**: `#layer/postgres`
- **상위 아키텍처 노트**: [[00-Index]], [[02-Storage-and-Auth]], [[storage-auth-flow.canvas]]
- **내부 모듈 의존성(Imports)**: [[mod__storage__database]]



## 정의된 클래스 / 상태 스키마
- 없음

## 정의된 함수 / 노드
- `def run(connection)`
- `async def main()`

## 소스 코드 미리보기 (`migrations/env.py`)

```python
import asyncio
from alembic import context
from storage.database import get_engine, metadata

def run(connection):
    context.configure(connection=connection, target_metadata=metadata)
    with context.begin_transaction():
        context.run_migrations()

async def main():
    engine = get_engine()
    async with engine.connect() as connection:
        await connection.run_sync(run)
    await engine.dispose()

asyncio.run(main())
```
