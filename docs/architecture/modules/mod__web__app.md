---
title: "src/web/app.py"
tags:
  - code
  - layer/web
---

# `src/web/app.py`

- **소속 계층 태그**: `#layer/web`
- **상위 아키텍처 노트**: [[00-Index]], [[01-Web-and-Editor]]
- **내부 모듈 의존성(Imports)**: [[mod__config__config]], [[mod__graph__supervisor_graph]], [[mod__models__llm]], [[mod__storage__accounts]], [[mod__storage__database]], [[mod__storage__history]], [[mod__storage__repository]], [[mod__web__auth]], [[mod__web__history_api]]

> Run: uv run uvicorn web.app:app --app-dir src --host 127.0.0.1 --port 8000.

## 정의된 클래스 / 상태 스키마
- `Message`
- `Draft`
- `Revision`

## 정의된 함수 / 노드
- `async def lifespan(app)`
- `async def authenticate(request, call_next)`
- `def initial_state()`
- `def invoke_graph(state)`
- `def document(state)`
- `def render_markdown(markdown)`
- `def snapshot(session)`
- `async def find_session(session_id)`
- `async def database_error(request, exc)`
- `async def run(session, response)`
- `def index()`
- `def config()`
- `async def health()`
- `async def create_session()`
- `async def list_sessions(limit, offset)`
- `async def get_session(session_id)`
- `async def save_draft(session_id, draft)`
- `async def copy_session(session_id, draft)`
- `def revise_passage(request)`
- `async def revise(session_id, request, idempotency_key)`
- `async def download_draft(session_id)`
- `async def send_message(session_id, message, idempotency_key)`
- `async def download(session_id)`

## 소스 코드 미리보기 (`src/web/app.py`)

```python
"""Run: uv run uvicorn web.app:app --app-dir src --host 127.0.0.1 --port 8000."""
import asyncio
from contextlib import asynccontextmanager
from copy import deepcopy
import logging
import json
from pathlib import Path
import secrets
from starlette.middleware.sessions import SessionMiddleware
from web import auth
from web.history_api import router as history_router
from storage import history
from storage import accounts

import bleach
import httpx
from fastapi import FastAPI, HTTPException, Query, Request, Header
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from storage import repository as store
from storage.database import get_engine
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from markdown_it import MarkdownIt
from pydantic import BaseModel, Field, field_validator

from config import config as settings

STATIC = Path(__file__).parent / "static"
tasks = set()
# Existing agents share a local vector store and output files: serialize runs.
run_lock = asyncio.Lock()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app):
    if len(settings.AUTH_SECRET) < 32:
        raise RuntimeError("AUTH_SECRET을 32자 이상으로 설정하세요.")
    await store.initialize()
    if await accounts.sync_admin_from_env(settings.ADMIN_EMAIL, settings.ADMIN_PASSWORD) == 'skipped':
        logger.warning('ADMIN_EMAIL/ADMIN_PASSWORD가 없어 관리자 계정 동기화를 건너뜁니다.')
    yield
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
    await get_engine().dispose()


app = FastAPI(title="DIV · Vibe Planner", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC), name="static")

app.add_middleware(SessionMiddleware, secret_key=settings.AUTH_SECRET or 'not-configured', session_cookie='div_oauth', same_site='lax', https_only=settings.AUTH_COOKIE_SECURE, max_age=600)
app.include_router(auth.router)
app.include_router(history_router)

@app.middleware('http')
async def authenticate(request: Request, call_next):
    if not request.url.path.startswith('/api/') or request.url.path.startswith('/api/auth/'):
        return await call_next(request)
    try:
        user = await auth.identify(request)
        if not user:
            return JSONResponse(status_code=401, content={'detail':'로그인이 필요합니다.'})
        if request.method not in {'GET','HEAD','OPTIONS'}:
            auth.check_origin(request)
            if not secrets.compare_digest(request.headers.get('x-csrf-token',''), user['csrf']):
                raise HTTPException(403, '요청을 확인할 수 없습니다.')
        token = auth.current_user.set(user)
        try:
            return await call_next(request)
        finally:
            auth.current_user.reset(token)
    except HTTPException as exc:
        return JSONResponse(status_code=exc.status_code, content={'detail':exc.detail})
    except SQLAlchemyError:
        return JSONResponse(status_code=503, content={'detail':'저장소에 연결할 수 없습니다.'})


def initial_state():
    return {
        "messages": [AIMessage(content="어떤 아이디어를 기획서로 만들어 볼까요? 대상 사용자와 원하는 결과를 함께 알려주세요.")],
        "awaiting_input": True, "input_request": None, "user_response": None,
        "completed_steps": "",
        "idea": {"planning_style": "", "rationale": "", "toc": [], "blueprint": [],
                 "last_decision": "", "messages": ""},
        "plan": {"sections": [], "final_markdown": "", "output_path": "", "visual_artifacts": []},
        "supervision": {"goal": "Produce a high-quality vibe-based planning document",
                        "last_decision": "ASK_USER", "current_task": "idea_structuring",
                        "reason": "", "pending_request": None, "request_type": "text",
```
