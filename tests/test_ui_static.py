"""Offline route and real-browser checks for the no-build interface."""
import os
from pathlib import Path
import shutil
import subprocess

from fastapi.testclient import TestClient
import pytest

from polytoken.api import create_app

ROOT = Path(__file__).resolve().parents[1]


def test_ui_mount_and_api_precedence(tmp_path, monkeypatch):
    # The static directory is resolved from the source, not the working directory.
    monkeypatch.chdir(tmp_path)
    with TestClient(create_app(reference=False, state_dir=tmp_path, log_dir=tmp_path)) as client:
        page = client.get('/')
        assert page.status_code == 200
        assert 'text/html' in page.headers['content-type']
        assert '<title>PolyToken' in page.text
        for filename in ('app.js', 'styles.css'):
            assert client.get('/' + filename).status_code == 200
        assert client.get('/investigations/unknown/report').status_code == 404
        assert client.get('/evidence/unknown').status_code == 404
        assert client.post('/investigations', json={'company': 'unknown'}).status_code == 422
        assert client.get('/.env').status_code == 404
        assert client.get('/src/polytoken/api.py').status_code == 404
        assert client.get('/%2e%2e/.env').status_code == 404


def test_ui_saved_reports_and_browser_flows():
    node = shutil.which('node')
    if not node:
        pytest.skip('Node is required for the optional headless UI check')
    env = os.environ.copy()
    # Use an existing Playwright installation; never install npm packages for this UI.
    bundled = Path.home() / '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules'
    if (bundled / 'playwright/package.json').exists():
        env['NODE_PATH'] = os.pathsep.join(filter(None, [env.get('NODE_PATH'), str(bundled)]))
    probe = subprocess.run([node, '-e', "require.resolve('playwright')"], env=env, capture_output=True)
    if probe.returncode:
        pytest.skip('Playwright is not installed; see web/README.md for the schema contract')
    args = [node, str(ROOT / 'web/check-ui.cjs')]
    if env.get('UI_SCREENSHOTS') == '1':
        args.append('--screenshots')
    result = subprocess.run(args, cwd=ROOT, env=env,
                            capture_output=True, text=True, timeout=180)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'UI checks passed' in result.stdout
