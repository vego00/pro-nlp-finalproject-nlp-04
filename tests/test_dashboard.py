"""Real PostgreSQL tests; set TEST_DATABASE_URL to a dedicated *_test database."""
import asyncio
import os
from pathlib import Path
import sys
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine
from langchain_core.messages import AIMessage, HumanMessage
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from web import app as dashboard
from storage import database, repository
from web import auth
from uuid import uuid4

@pytest.fixture
def client(monkeypatch):
    url = os.getenv('TEST_DATABASE_URL')
    if not url:
        pytest.skip('TEST_DATABASE_URL required')
    assert make_url(url).database.endswith('_test'), 'Only dedicated test databases are allowed'
    monkeypatch.setattr(dashboard.settings, 'DATABASE_URL', url)
    monkeypatch.setattr(dashboard.settings, 'ADMIN_EMAIL', '')
    monkeypatch.setattr(dashboard.settings, 'ADMIN_PASSWORD', '')
    database.engine = None
    async def reset():
        async with database.get_engine().begin() as c:
            await c.execute(text('TRUNCATE sessions, documents, users CASCADE'))
        await database.get_engine().dispose()
    asyncio.run(reset())
    dashboard.run_lock = asyncio.Lock()
    auth.attempts.clear()
    class AuthClient(TestClient):
        def post(self, url, **kwargs):
            headers = kwargs.setdefault('headers', {})
            headers.setdefault('Idempotency-Key', str(uuid4()))
            return super().post(url, **kwargs)
    with AuthClient(dashboard.app) as c:
        async def provision():
            async with database.get_engine().begin() as conn:
                for uid,email in [('test-user','test@example.com'),('other-user','other@example.com')]:
                    await conn.execute(text('INSERT INTO users(id,key,email,password_hash,is_admin) VALUES (:id,:id,:email,:hash,true)'), {'id':uid,'email':email,'hash':auth.hasher.hash('test-password-123')})
        c.portal.call(provision)
        c.headers['X-Requested-With'] = 'DIV'
        assert c.post('/api/auth/login',json={'email':'test@example.com','password':'test-password-123'}).status_code == 200
        c.headers['X-CSRF-Token'] = c.get('/api/auth/me').json()['csrf']
        yield c
    database.engine = None


def create(client):
    result = client.post('/api/sessions')
    assert result.status_code == 201, result.text
    return result.json()['id']


def save(client, sid, body='hello', revision=0, document=None):
    return client.put(f'/api/sessions/{sid}/draft', json={'markdown':body, 'document':document, 'base_revision':revision})


def test_persistence_validation_isolation(client):
    sid, other = create(client), create(client)
    document = {'type':'doc', 'content':[{'type':'paragraph','content':[{'type':'text','text':'hello'}]}]}
    assert save(client, sid, '<script>x</script>', document=document).status_code == 200
    data = client.get(f'/api/sessions/{sid}').json()
    assert data['draft_document'] == document and data['draft_revision'] == 1
    assert '<script>' not in data['draft_html']
    assert client.get(f'/api/sessions/{other}').json()['draft'] == ''
    assert client.get(f'/api/sessions/{sid}/draft/download').text == '<script>x</script>'
    assert client.get(f'/api/sessions/{sid}/download').status_code == 404
    assert client.get('/api/sessions/missing').status_code == 404
    assert save(client, sid, 'x'*200001, 1).status_code == 422
    assert save(client, sid, revision=1, document={'type':'script'}).status_code == 422
    assert client.put(f'/api/sessions/{sid}/draft', json={'markdown':'x'}).status_code == 422
    assert client.get('/api/sessions?limit=101').status_code == 422
    assert len(client.get('/api/sessions').json()) == 2


def test_atomic_conflict_and_copy(client):
    sid = create(client)
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda body: save(client, sid, body), ['first','second']))
    assert sorted(r.status_code for r in results) == [200,409]
    original = client.get(f'/api/sessions/{sid}').json()['draft']
    copy = client.post(f'/api/sessions/{sid}/copy', json={'markdown':'my version','base_revision':0}).json()
    assert copy['id'] != sid and copy['draft'] == 'my version'
    assert client.get(f'/api/sessions/{sid}').json()['draft'] == original


def test_graph_and_failure_preserve_draft(client, monkeypatch):
    sid = create(client)
    save(client, sid, 'user draft')
    def invoke(state):
        state['messages'] += [HumanMessage(content='idea'), AIMessage(content='done')]
        state['plan']['final_markdown'] = '# AI result'
        return state
    monkeypatch.setattr(dashboard, 'invoke_graph', invoke)
    assert client.post(f'/api/sessions/{sid}/messages', json={'text':'idea'}).status_code == 202
    import time
    for _ in range(200):
        data = client.get(f'/api/sessions/{sid}').json()
        if data['status'] != 'running': break
        time.sleep(.01)
    assert data['status'] == 'ready' and data['markdown'] == '# AI result'
    assert data['draft'] == 'user draft' and data['messages'][-1]['content'] == 'done'
    def fail(state):
        state['plan']['final_markdown'] = 'broken'
        raise RuntimeError('private key')
    monkeypatch.setattr(dashboard, 'invoke_graph', fail)
    client.post(f'/api/sessions/{sid}/messages', json={'text':'retry'})
    for _ in range(200):
        data = client.get(f'/api/sessions/{sid}').json()
        if data['status'] != 'running': break
        time.sleep(.01)
    assert data['status'] == 'error' and data['markdown'] == '# AI result'
    assert 'private key' not in data['error']


def test_revision_preview(client, monkeypatch):
    sid = create(client)
    save(client, sid, 'original')
    monkeypatch.setattr(dashboard, 'revise_passage', lambda request: 'revised')
    result = client.post(f'/api/sessions/{sid}/revise', json={'selection':'original','instruction':'shorten'})
    assert result.json()['text'] == 'revised'
    assert client.get(f'/api/sessions/{sid}').json()['draft'] == 'original'


def test_codec():
    state = dashboard.initial_state()
    state['messages'] = [HumanMessage(content='hello', id='m1'), AIMessage(content='world', additional_kwargs={'x':1})]
    assert repository.decode(repository.encode(state)) == state


def test_llm_model_selection(monkeypatch):
    from models.llm import get_llm, get_mini_llm
    from config import config
    assert "qwen3.8:27b" in config.OLLAMA_MODEL_PRESETS
    assert "Qwen/Qwen3.8-27B" in config.HF_MODEL_PRESETS
    assert "gemini-2.5-flash" in config.GEMINI_MODEL_PRESETS
    monkeypatch.setattr(config, "LLM_PROVIDER", "ollama")
    monkeypatch.setattr(config, "LLM_MODEL", "qwen3.8:27b")
    monkeypatch.setattr(config, "LLM_MINI_MODEL", "test-small")
    assert get_llm(json_mode=True).model == "qwen3.8:27b"
    assert get_llm(json_mode=True).format == "json"
    assert get_mini_llm().model == "test-small"
    monkeypatch.setattr(config, "LLM_PROVIDER", "gemini")
    monkeypatch.setattr(config, "LLM_MODEL", "gemini-2.5-flash")
    monkeypatch.setattr(config, "GEMINI_API_KEY", None)
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        get_llm()
    monkeypatch.setattr(config, "GEMINI_API_KEY", "test-gemini-key")
    gemini_llm = get_llm(json_mode=True)
    assert "gemini-2.5-flash" in gemini_llm.model
    assert gemini_llm.response_mime_type == "application/json"
    monkeypatch.setattr(config, "LLM_PROVIDER", "invalid")
    with pytest.raises(ValueError, match="LLM_PROVIDER"):
        get_llm()



def test_form_validation_and_draft_context(client, monkeypatch):
    sid = create(client)
    save(client, sid, 'attached draft')
    captured = []
    def invoke(state):
        captured.append(state['user_response'])
        state['supervision'].update(request_type='idea_form', last_decision='ASK_USER')
        state['input_request'] = [{'current_section':'audience','question':'누구?'}]
        return state
    monkeypatch.setattr(dashboard, 'invoke_graph', invoke)
    assert client.post(f'/api/sessions/{sid}/messages',json={'text':' '}).status_code == 422
    client.post(f'/api/sessions/{sid}/messages',json={'text':'improve','include_draft':True})
    import time
    for _ in range(200):
        if client.get(f'/api/sessions/{sid}').json()['status'] != 'running': break
        time.sleep(.01)
    assert 'attached draft' in captured[0]
    assert client.post(f'/api/sessions/{sid}/messages',json={'text':'hello'}).status_code == 422
    assert client.post(f'/api/sessions/{sid}/messages',json={'answers':{'audience':{'value':'학생'}}}).status_code == 202


def test_database_failure_returns_503(client, monkeypatch):
    from sqlalchemy.exc import OperationalError
    async def fail(*args):
        raise OperationalError('private', {}, Exception('secret'))
    monkeypatch.setattr(repository, 'get', fail)
    result = client.get('/api/sessions/any')
    assert result.status_code == 503 and 'secret' not in result.text


def test_import_idempotence_and_invalid_file(client, tmp_path):
    import subprocess
    import json
    sid = 'a' * 32
    source = tmp_path / f'{sid}.json'
    original = json.dumps({'markdown':'imported', 'document':None})
    source.write_text(original)
    (tmp_path / f'{"b" * 32}.json').write_text('{broken')
    env = dict(os.environ, PYTHONPATH='src', DATABASE_URL=os.environ['TEST_DATABASE_URL'])
    command = [sys.executable, '-m', 'storage.import_drafts', str(tmp_path), '--owner-email', 'test@example.com']
    result = subprocess.run(command + ['--dry-run'], env=env, capture_output=True, text=True, check=True)
    assert '검증 완료' in result.stdout and '실패' in result.stdout
    assert client.get(f'/api/sessions/{sid}').status_code == 404
    subprocess.run(command, env=env, capture_output=True, check=True)
    again = subprocess.run(command, env=env, capture_output=True, text=True, check=True)
    assert '건너뜀' in again.stdout
    assert client.get(f'/api/sessions/{sid}').json()['draft'] == 'imported'
    assert source.read_text() == original


def test_history_restore_and_ownership(client):
    sid = create(client)
    save(client, sid, 'version one')
    save(client, sid, 'version two', 1)
    versions = client.get(f'/api/sessions/{sid}/versions').json()
    old = next(v for v in versions if v['revision'] == 1)
    response = client.post(f'/api/sessions/{sid}/versions/{old["id"]}/restore', json={'base_revision':2})
    assert response.json()['draft'] == 'version one'
    assert response.json()['draft_revision'] == 3
    assert client.get(f'/api/sessions/{sid}/versions/{old["id"]}').json()['markdown'] == 'version one'
    assert client.post(f'/api/sessions/{sid}/versions/{old["id"]}/restore', json={'base_revision':2}).status_code == 409
    client.post('/api/auth/logout')
    assert client.get(f'/api/sessions/{sid}').status_code == 401
    client.post('/api/auth/login',json={'email':'other@example.com','password':'test-password-123'})
    client.headers['X-CSRF-Token'] = client.get('/api/auth/me').json()['csrf']
    for suffix in ['', '/draft/download', '/download', '/versions', '/jobs']:
        assert client.get(f'/api/sessions/{sid}{suffix}').status_code == 404
    assert client.get('/api/sessions').json() == []


def test_idempotency_and_job_result(client, monkeypatch):
    import time
    sid = create(client)
    calls = []
    def invoke(state):
        calls.append(True)
        state['plan']['final_markdown'] = 'generated'
        return state
    monkeypatch.setattr(dashboard, 'invoke_graph', invoke)
    headers = {'Idempotency-Key':'same-request-key'}
    url = f'/api/sessions/{sid}/messages'
    first = client.post(url,json={'text':'idea'},headers=headers)
    job_id = first.json()['job_id']
    for _ in range(200):
        job = client.get('/api/jobs/'+job_id).json()
        if job['status'] != 'running': break
        time.sleep(.01)
    assert job['status'] == 'succeeded' and job['result']['markdown'] == 'generated'
    assert client.post(url,json={'text':'idea'},headers=headers).json()['job_id'] == job_id
    assert len(calls) == 1
    assert client.post(url,json={'text':'changed'},headers=headers).status_code == 409
    assert any(v['kind']=='generated' for v in client.get(f'/api/sessions/{sid}/versions').json())


def test_csrf_and_login_failure(client):
    sid = create(client)
    assert client.put(f'/api/sessions/{sid}/draft',json={'markdown':'bad','base_revision':0},headers={'X-CSRF-Token':'wrong'}).status_code == 403
    assert client.post('/api/auth/login',json={'email':'test@example.com','password':'wrong'}).status_code == 401
    assert client.post('/api/auth/login',json={'email':'test@example.com','password':'test-password-123'},headers={'Origin':'https://evil.example'}).status_code == 403


def test_google_disabled(client):
    if not dashboard.settings.GOOGLE_CLIENT_ID:
        assert client.get('/api/auth/google').status_code == 503


def test_google_requires_admin_enabled_account(client, monkeypatch):
    async def fake_token(request):
        return {'userinfo': {'sub':'google-subject', 'email':'test@example.com', 'email_verified':True}}
    monkeypatch.setattr(auth.oauth.google, 'authorize_access_token', fake_token)
    assert client.get('/api/auth/google/callback').status_code == 401
    async def enable():
        async with database.get_engine().begin() as c:
            await c.execute(text("UPDATE users SET allow_google=true WHERE id='test-user'"))
    client.portal.call(enable)
    response = client.get('/api/auth/google/callback', follow_redirects=False)
    assert response.status_code == 303
    assert client.get('/api/auth/me').json()['id'] == 'test-user'
    async def unverified(request):
        return {'userinfo': {'sub':'new-subject', 'email':'test@example.com', 'email_verified':False}}
    monkeypatch.setattr(auth.oauth.google, 'authorize_access_token', unverified)
    assert client.get('/api/auth/google/callback').status_code == 401


def test_version_restore_cannot_read_other_document(client):
    sid, other = create(client), create(client)
    save(client,sid,'private history')
    vid = client.get(f'/api/sessions/{sid}/versions').json()[0]['id']
    assert client.get(f'/api/sessions/{other}/versions/{vid}').status_code == 404
    assert client.post(f'/api/sessions/{other}/versions/{vid}/restore',json={'base_revision':0}).status_code == 404


def test_concurrent_duplicate_and_draft_save_during_run(client, monkeypatch):
    import threading
    import time
    entered, release = threading.Event(), threading.Event()
    sid = create(client)
    save(client, sid, 'original context')
    calls = []
    def invoke(state):
        calls.append(state['user_response'])
        entered.set()
        assert release.wait(10)
        state['plan']['final_markdown'] = 'AI output'
        return state
    monkeypatch.setattr(dashboard, 'invoke_graph', invoke)
    payload = {'text':'improve','include_draft':True}
    try:
        with ThreadPoolExecutor(2) as pool:
            replies = list(pool.map(lambda _: client.post(f'/api/sessions/{sid}/messages',json=payload,headers={'Idempotency-Key':'concurrent-key'}),range(2)))
        assert [r.status_code for r in replies] == [202,202]
        assert replies[0].json()['job_id'] == replies[1].json()['job_id']
        assert entered.wait(3)
        assert save(client,sid,'edited during AI',1).status_code == 200
    finally:
        release.set()
    for _ in range(200):
        job = client.get('/api/jobs/'+replies[0].json()['job_id']).json()
        if job['status'] != 'running': break
        time.sleep(.01)
    assert job['status'] == 'succeeded' and len(calls) == 1
    assert 'original context' in calls[0]
    assert client.get(f'/api/sessions/{sid}').json()['draft'] == 'edited during AI'


def test_env_admin_sync_creates_rotates_and_adopts(client):
    from storage import accounts
    sid = create(client)
    async def query(sql, **params):
        async with database.get_engine().begin() as c:
            result = await c.execute(text(sql), params)
            return result.all() if result.returns_rows else None
    did = client.portal.call(lambda: query('SELECT document_id FROM sessions WHERE id=:sid', sid=sid))[0][0]
    client.portal.call(lambda: query('UPDATE documents SET owner_id=:local WHERE id=:did', local=accounts.LOCAL_OWNER, did=did))
    sync = lambda email, password: client.portal.call(accounts.sync_admin_from_env, email, password)

    assert sync('', '') == 'skipped'
    with pytest.raises(RuntimeError):
        sync('admin@example.com', '')
    with pytest.raises(ValueError):
        sync('admin@example.com', 'abc')

    assert sync(' Admin@Example.com ', 'abcd') == 'created'
    admin_id, is_admin = client.portal.call(lambda: query("SELECT id,is_admin FROM users WHERE email='admin@example.com'"))[0]
    assert is_admin
    assert client.portal.call(lambda: query('SELECT owner_id FROM documents WHERE id=:did', did=did))[0][0] == admin_id
    assert sync('admin@example.com', 'abcd') == 'unchanged'

    login = lambda password: client.post('/api/auth/login', json={'email': 'admin@example.com', 'password': password})
    assert login('abcd').status_code == 200
    assert client.portal.call(lambda: query('SELECT count(*) FROM login_sessions WHERE user_id=:id', id=admin_id))[0][0] == 1

    assert sync('admin@example.com', 'second-password-456') == 'updated'
    assert client.portal.call(lambda: query('SELECT count(*) FROM login_sessions WHERE user_id=:id', id=admin_id))[0][0] == 0
    assert login('abcd').status_code == 401
    assert login('second-password-456').status_code == 200

    client.portal.call(lambda: query('UPDATE users SET is_admin=false, active=false WHERE id=:id', id=admin_id))
    assert sync('admin@example.com', 'second-password-456') == 'updated'
    assert client.portal.call(lambda: query('SELECT is_admin, active FROM users WHERE id=:id', id=admin_id))[0] == (True, True)
