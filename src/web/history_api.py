from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from storage import repository as store, history
from web.auth import owner_id

router = APIRouter()

@router.get('/api/sessions/{sid}/versions')
async def versions(sid: str, limit: int = Query(20,ge=1,le=100), offset: int = Query(0,ge=0)):
    session = await store.get(sid)
    return await history.versions(session['document_id'],limit,offset)

@router.get('/api/sessions/{sid}/versions/{vid}')
async def version(sid: str, vid: int):
    session = await store.get(sid)
    return await history.version(session['document_id'],vid)

class Restore(BaseModel):
    base_revision: int = Field(ge=0)

@router.post('/api/sessions/{sid}/versions/{vid}/restore')
async def restore(sid: str, vid: int, body: Restore):
    from web.app import snapshot
    session = await store.get(sid)
    old = await history.version(session['document_id'],vid)
    return snapshot(await store.save(sid,old['markdown'],old['document'],body.base_revision,reason='restore'))

@router.get('/api/sessions/{sid}/jobs')
async def jobs(sid: str, limit: int = Query(20,ge=1,le=100), offset: int = Query(0,ge=0)):
    await store.get(sid)
    return await history.job_list(owner_id(),sid,limit,offset)

@router.get('/api/jobs/{job_id}')
async def job(job_id: str):
    return await history.get_job(owner_id(),job_id)
