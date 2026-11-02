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

@pytest.fixture
def client(monkeypatch):
    url = os.getenv('TEST_DATABASE_URL')
    if not url:
        pytest.skip('TEST_DATABASE_URL required')
    assert make_url(url).database.endswith('_test'), 'Only dedicated test databases are allowed'
    monkeypatch.setattr(dashboard.settings, 'DATABASE_URL', url)
    database.engine = None
    async def reset():
        async with database.get_engine().begin() as c:
            await c.execute(text('TRUNCATE sessions, documents, users CASCADE'))
        await database.get_engine().dispose()
    asyncio.run(reset())
    dashboard.run_lock = asyncio.Lock()
    with TestClient(dashboard.app) as c:
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
    monkeypatch.setattr(config, "LLM_PROVIDER", "ollama")
    monkeypatch.setattr(config, "LLM_MODEL", "test-main")
    monkeypatch.setattr(config, "LLM_MINI_MODEL", "test-small")
    assert get_llm(json_mode=True).model == "test-main"
    assert get_llm(json_mode=True).format == "json"
    assert get_mini_llm().model == "test-small"
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
    command = [sys.executable, '-m', 'storage.import_drafts', str(tmp_path)]
    result = subprocess.run(command + ['--dry-run'], env=env, capture_output=True, text=True, check=True)
    assert '검증 완료' in result.stdout and '실패' in result.stdout
    assert client.get(f'/api/sessions/{sid}').status_code == 404
    subprocess.run(command, env=env, capture_output=True, check=True)
    again = subprocess.run(command, env=env, capture_output=True, text=True, check=True)
    assert '건너뜀' in again.stdout
    assert client.get(f'/api/sessions/{sid}').json()['draft'] == 'imported'
    assert source.read_text() == original
