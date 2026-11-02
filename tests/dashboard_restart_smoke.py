"""Restart/API/browser checks. Requires a migrated, dedicated TEST_DATABASE_URL."""
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time

import httpx
import psycopg
from psycopg.types.json import Jsonb
from sqlalchemy.engine import make_url


def main():
    url = os.environ['TEST_DATABASE_URL']
    if not (make_url(url).database or '').endswith('_test'):
        raise RuntimeError('Dedicated *_test database required')
    connection_url = make_url(url).set(drivername='postgresql').render_as_string(hide_password=False)
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    base = f'http://127.0.0.1:{port}'
    env = dict(os.environ, DATABASE_URL=url, PYTHONPATH='src', DASHBOARD_URL=base)

    with tempfile.TemporaryFile(mode='w+') as log:
        def start():
            process = subprocess.Popen(
                [sys.executable, '-m', 'uvicorn', 'web.app:app', '--app-dir', 'src', '--port', str(port)],
                env=env, stdout=log, stderr=subprocess.STDOUT,
            )
            for _ in range(100):
                if process.poll() is not None:
                    break
                try:
                    if httpx.get(base + '/api/config', timeout=1).status_code == 200:
                        return process
                except httpx.HTTPError:
                    pass
                time.sleep(.1)
            process.terminate()
            process.wait(timeout=10)
            log.seek(0)
            raise RuntimeError(log.read())

        process = start()
        try:
            sid = httpx.post(base + '/api/sessions').json()['id']
            endpoint = f'{base}/api/sessions/{sid}'
            draft = {'type': 'doc', 'content': [{'type': 'paragraph', 'content': [{'type': 'text', 'text': 'restart-proof'}]}]}
            assert httpx.put(endpoint + '/draft', json={'markdown': 'restart-proof', 'document': draft, 'base_revision': 0}).status_code == 200
            # Seed a completed graph boundary; no paid/local model is required.
            with psycopg.connect(connection_url) as connection:
                state = connection.execute('SELECT state FROM sessions WHERE id=%s', (sid,)).fetchone()[0]
                state['messages'].extend([
                    {'type': 'human', 'data': {'content': 'saved question', 'type': 'human', 'id': 'question'}},
                    {'type': 'ai', 'data': {'content': 'saved answer', 'type': 'ai', 'id': 'answer'}},
                ])
                state['supervision'].update(request_type='idea_form')
                state['input_request'] = [{'current_section': 'audience', 'question': '누구?'}]
                state['plan']['output_path'] = '/missing/generated.md'
                connection.execute('UPDATE sessions SET state=%s, markdown=%s WHERE id=%s', (Jsonb(state), '# persisted AI result', sid))
            process.kill()
            process.wait()
            process = start()
            result = httpx.get(endpoint).json()
            assert result['draft'] == 'restart-proof' and result['draft_document'] == draft
            assert result['messages'][-1]['content'] == 'saved answer'
            assert result['questions'][0]['current_section'] == 'audience'
            assert httpx.get(endpoint + '/download').text == '# persisted AI result'
            with psycopg.connect(connection_url) as connection:
                connection.execute("UPDATE sessions SET status='running', run_token='interrupted' WHERE id=%s", (sid,))
            process.kill()
            process.wait()
            process = start()
            result = httpx.get(endpoint).json()
            assert result['status'] == 'error' and result['draft'] == 'restart-proof'
            print('Process restart, messages, rich draft, AI result, interrupted run recovery: OK', flush=True)
            subprocess.run([sys.executable, str(Path(__file__).with_name('dashboard_browser_smoke.py'))], env=env, check=True)
        finally:
            process.terminate()
            process.wait(timeout=15)


if __name__ == '__main__':
    main()
