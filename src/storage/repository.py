"""Transactional session operations. Never hold a connection during model calls."""
from uuid import uuid4
from sqlalchemy import select, update, insert, func, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from langchain_core.messages import messages_to_dict, messages_from_dict
from fastapi import HTTPException
from storage.database import get_engine, users, documents as d, sessions as s

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
        if version != '001_storage':
            raise RuntimeError('alembic upgrade head 실행이 필요합니다.')
        await c.execute(pg_insert(users).values(id=OWNER, key='local').on_conflict_do_nothing())
        await c.execute(update(s).where(s.c.status == 'running').values(status='error', error='서버 재시작으로 작업이 중단되었습니다. 다시 요청하세요.', run_token=None))


async def create(state, markdown='', document=None, session_id=None):
    sid, did = session_id or uuid4().hex, str(uuid4())
    async with get_engine().begin() as c:
        await c.execute(insert(d).values(id=did, owner_id=OWNER, title=title(markdown), draft=markdown, draft_document=document, draft_revision=0))
        await c.execute(insert(s).values(id=sid, document_id=did, state=encode(state), state_schema_version=1, markdown='', status='ready'))
    return await get(sid)


async def get(sid):
    async with get_engine().connect() as c:
        row = (await c.execute(select(s, d.c.title, d.c.draft, d.c.draft_document, d.c.draft_revision, d.c.updated_at).join(d).where(s.c.id == sid, d.c.owner_id == OWNER))).mappings().first()
    if row is None:
        raise HTTPException(404, '세션이 없습니다. 새 문서를 시작하세요.')
    result = dict(row)
    if result['state_schema_version'] != 1:
        raise HTTPException(503, '지원하지 않는 저장 상태 버전입니다.')
    result['state'] = decode(result['state'])
    return result


async def listing(limit, offset):
    async with get_engine().connect() as c:
        rows = await c.execute(select(s.c.id, d.c.title, s.c.status, d.c.updated_at).join(d).where(d.c.owner_id == OWNER).order_by(d.c.updated_at.desc(), s.c.id).limit(limit).offset(offset))
        return [dict(row) for row in rows.mappings()]


async def save(sid, markdown, document, revision):
    session = await get(sid)
    async with get_engine().begin() as c:
        result = await c.execute(update(d).where(d.c.id == session['document_id'], d.c.owner_id == OWNER, d.c.draft_revision == revision).values(draft=markdown, draft_document=document, draft_revision=revision + 1, title=title(markdown), updated_at=func.now()).returning(d.c.title, d.c.draft, d.c.draft_document, d.c.draft_revision, d.c.updated_at))
        saved = result.mappings().first()
        if saved is None:
            raise HTTPException(409, '다른 곳에서 수정된 문서입니다. 최신본을 열거나 사본으로 저장하세요.')
        session.update(saved)
    return session


async def claim(sid, expected_state):
    await get(sid)
    token = uuid4().hex
    async with get_engine().begin() as c:
        result = await c.execute(update(s).where(s.c.id == sid, s.c.status != 'running', s.c.state == encode(expected_state)).values(status='running', error=None, run_token=token))
        if not result.rowcount:
            raise HTTPException(409, '현재 요청을 처리 중입니다.')
    return token


async def checkpoint(session, token, markdown, status='running', error=None):
    async with get_engine().begin() as c:
        result = await c.execute(update(s).where(s.c.id == session['id'], s.c.run_token == token).values(state=encode(session['state']), markdown=markdown, status=status, error=error, run_token=token if status == 'running' else None))
        if not result.rowcount:
            raise RuntimeError('실행 소유권이 변경되었습니다.')
        await c.execute(update(d).where(d.c.id == session['document_id']).values(updated_at=func.now()))
