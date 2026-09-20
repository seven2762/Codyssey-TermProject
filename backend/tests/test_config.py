"""별도 프로세스에서 .env 설정과 실제 앱의 HTTPS 쿠키 동작을 확인한다."""

import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture
def config_file(tmp_path):
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    return Path(shutil.copy(BACKEND_DIR / "app/config.py", app_dir / "config.py"))


@pytest.mark.parametrize(
    "settings, error_name",
    [
        ({}, "SESSION_SECRET_KEY"),
        ({"SESSION_SECRET_KEY": ""}, "SESSION_SECRET_KEY"),
        ({"SESSION_SECRET_KEY": "  "}, "SESSION_SECRET_KEY"),
        ({"SESSION_MAX_AGE": "0"}, "SESSION_MAX_AGE"),
        ({"SESSION_MAX_AGE": "-1"}, "SESSION_MAX_AGE"),
        ({"SESSION_MAX_AGE": "abc"}, "SESSION_MAX_AGE"),
        ({"SESSION_HTTPS_ONLY": "yes"}, "SESSION_HTTPS_ONLY"),
    ],
)
def test_invalid_session_settings_fail_startup(config_file, settings, error_name):
    env = os.environ.copy()
    for name in ("SESSION_SECRET_KEY", "SESSION_MAX_AGE", "SESSION_HTTPS_ONLY"):
        env.pop(name, None)
    if error_name != "SESSION_SECRET_KEY":
        env["SESSION_SECRET_KEY"] = "test-config-secret"
    env.update(settings)
    result = subprocess.run([sys.executable, str(config_file)], env=env, capture_output=True, text=True)
    assert result.returncode != 0
    assert error_name in result.stderr


def test_dotenv_and_environment_precedence(config_file, tmp_path):
    (tmp_path / ".env").write_text(
        "SESSION_SECRET_KEY=dotenv-test-key\nSESSION_MAX_AGE=1800\n"
        "SESSION_HTTPS_ONLY=true\nDATABASE_PATH=state/test.db\n",
        encoding="utf-8",
    )
    env = os.environ.copy()
    for name in ("SESSION_SECRET_KEY", "SESSION_MAX_AGE", "SESSION_HTTPS_ONLY", "DATABASE_PATH"):
        env.pop(name, None)
    script = """
import runpy, sys
config = runpy.run_path(sys.argv[1])
assert config['SESSION_SECRET_KEY'] == sys.argv[2]
assert config['SESSION_MAX_AGE'] == int(sys.argv[3])
assert config['SESSION_HTTPS_ONLY'] is True
assert config['DATABASE_PATH'] == config['BACKEND_DIR'] / 'state/test.db'
"""
    for settings, expected_key, expected_age in [
        ({}, "dotenv-test-key", "1800"),
        ({"SESSION_SECRET_KEY": "shell-test-key", "SESSION_MAX_AGE": "600"}, "shell-test-key", "600"),
    ]:
        result = subprocess.run(
            [sys.executable, "-c", script, str(config_file), expected_key, expected_age],
            env={**env, **settings}, capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stderr


def test_https_cookie_is_not_sent_over_http(tmp_path):
    env = {
        **os.environ,
        "PYTHONPATH": str(BACKEND_DIR),
        "DATABASE_PATH": str(tmp_path / "https.db"),
        "SESSION_SECRET_KEY": "https-cookie-test-secret",
        "SESSION_MAX_AGE": "120",
        "SESSION_HTTPS_ONLY": "true",
    }
    script = """
from fastapi.testclient import TestClient
from app.main import app
credentials = {'username': 'https_user', 'password': 'a long test password'}
with TestClient(app, base_url='https://testserver', headers={'X-Requested-With': 'XMLHttpRequest'}) as client:
    assert client.post('/api/signup', json=credentials).status_code == 201
    response = client.post('/api/login', json=credentials)
    assert response.status_code == 200
    assert 'secure' in response.headers['set-cookie'].lower()
    assert 'Max-Age=120' in response.headers['set-cookie']
    assert client.get('/api/me').status_code == 200
    assert client.get('http://testserver/api/me').status_code == 401
"""
    result = subprocess.run(
        [sys.executable, "-c", script], cwd=tmp_path, env=env, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
