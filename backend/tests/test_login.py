"""로그인·로그아웃·쿠키·접근 제어를 실제 라우터와 임시 SQLite로 검증한다."""

from base64 import b64decode
import json
from sqlite3 import OperationalError as SQLiteOperationalError
import time

from fastapi.testclient import TestClient
from itsdangerous import TimestampSigner
import pytest
from sqlalchemy import select
from sqlalchemy.exc import OperationalError

PASSWORD = "  a long password phrase  "
CREDENTIALS = {"username": "charles", "password": PASSWORD}
COOKIE = "askmate_session"


@pytest.fixture
def registered_user(client):
    response = client.post("/api/signup", json=CREDENTIALS)
    assert response.status_code == 201
    return response.json()


def test_login_and_current_user(client, registered_user, caplog):
    from app.db_connect import SessionLocal
    from app.models.user import User

    with SessionLocal() as db:
        original_hash = db.scalar(select(User.password_hash))
    caplog.set_level("INFO")
    response = client.post("/api/login", json={"username": " CHARLES ", "password": PASSWORD})
    assert response.status_code == 200
    assert response.json() == registered_user
    cookie_header = response.headers["set-cookie"].lower()
    assert all(flag in cookie_header for flag in ("httponly", "samesite=lax", "path=/", "max-age=3600"))
    assert "secure" not in cookie_header
    assert response.headers["cache-control"] == "no-store"

    cookie = client.cookies.get(COOKIE)
    assert json.loads(b64decode(cookie.split(".")[0])) == {"user_id": registered_user["id"]}
    me = client.get("/api/me")
    assert me.status_code == 200
    assert me.json() == registered_user
    assert me.headers["cache-control"] == "no-store"
    assert "set-cookie" not in me.headers  # 조회만으로 만료 시각을 갱신하지 않는다.
    with SessionLocal() as db:
        assert db.scalar(select(User.password_hash)) == original_hash
    assert "login_success user_id=" in caplog.text
    for secret in (PASSWORD, original_hash, cookie):
        assert secret not in caplog.text
        assert secret not in response.text


@pytest.mark.parametrize(
    "credentials",
    [
        {"username": "unknown", "password": PASSWORD},
        {"username": "charles", "password": "wrong password"},
        {"username": "charles", "password": PASSWORD.strip()},
        {"username": "charles", "password": PASSWORD.upper()},
    ],
)
def test_invalid_credentials(client, registered_user, credentials, caplog):
    response = client.post("/api/login", json=credentials)
    assert response.status_code == 401
    assert response.json() == {"detail": "사용자명 또는 비밀번호가 올바르지 않습니다."}
    assert "set-cookie" not in response.headers
    assert client.get("/api/me").status_code == 401
    assert "login_failure" in caplog.text
    assert credentials["password"] not in caplog.text


@pytest.mark.parametrize(
    "payload",
    [
        {"username": "charles"},
        {"password": PASSWORD},
        {"username": "   ", "password": PASSWORD},
        {"username": "charles", "password": ""},
        {"username": "charles", "password": "p" * 129},
        {"username": "charles", "password": 123},
        {"username": "charles", "password": {"secret": PASSWORD}},
        [PASSWORD],
    ],
)
def test_login_validation_does_not_echo_input(client, payload):
    response = client.post("/api/login", json=payload)
    assert response.status_code == 422
    assert PASSWORD not in response.text
    assert all(set(error) == {"type", "loc", "msg"} for error in response.json()["detail"])
    assert "set-cookie" not in response.headers


@pytest.mark.parametrize("password", ["p" * 15, "p" * 128, "공백과 유니코드를 포함한 비밀번호입니다"])
def test_signup_passwords_can_log_in(client, password):
    credentials = {"username": "boundary_user", "password": password}
    assert client.post("/api/signup", json=credentials).status_code == 201
    assert client.post("/api/login", json=credentials).status_code == 200


def test_logout_and_repeated_logout(client, registered_user, caplog):
    caplog.set_level("INFO")
    assert client.post("/api/login", json=CREDENTIALS).status_code == 200
    response = client.post("/api/logout")
    assert response.status_code == 204
    assert response.content == b""
    assert "expires=Thu, 01 Jan 1970" in response.headers["set-cookie"]
    assert client.cookies.get(COOKIE) is None
    assert client.get("/api/me").status_code == 401
    assert client.get("/chat", follow_redirects=False).headers["location"] == "/login"
    assert client.post("/api/chat", json={"question": "hello"}).status_code == 401
    assert client.post("/api/logout").status_code == 204
    assert "logout_success user_id=" in caplog.text


def test_browsers_and_account_switching(application, client, registered_user, csrf_headers):
    other_credentials = {"username": "another", "password": PASSWORD}
    other_user = client.post("/api/signup", json=other_credentials).json()
    assert client.post("/api/login", json=CREDENTIALS).status_code == 200
    with TestClient(application, headers=csrf_headers) as second_browser:
        assert second_browser.get("/api/me").status_code == 401
        assert second_browser.post("/api/login", json=other_credentials).status_code == 200
        assert client.get("/api/me?user_id=" + str(other_user["id"])).json() == registered_user
        assert client.post("/api/login", json=other_credentials).status_code == 200
        assert client.get("/api/me").json() == other_user
        assert client.post("/api/logout").status_code == 204
        assert second_browser.get("/api/me").json() == other_user


@pytest.mark.parametrize("cookie_kind", ["tampered", "expired", "wrong_key"])
def test_invalid_cookies_are_anonymous(client, registered_user, monkeypatch, cookie_kind):
    from app.config import SESSION_SECRET_KEY

    if cookie_kind == "expired":
        issued_at = int(time.time()) - 3601
        with monkeypatch.context() as patch:
            patch.setattr(TimestampSigner, "get_timestamp", lambda self: issued_at)
            assert client.post("/api/login", json=CREDENTIALS).status_code == 200
        cookie = client.cookies.get(COOKIE)
    else:
        assert client.post("/api/login", json=CREDENTIALS).status_code == 200
        cookie = client.cookies.get(COOKIE)
        if cookie_kind == "tampered":
            cookie = "A" + cookie[1:]
        else:
            data = TimestampSigner(SESSION_SECRET_KEY).unsign(cookie)
            cookie = TimestampSigner("different-test-key").sign(data).decode()
    client.cookies.clear()
    client.cookies.set(COOKIE, cookie)
    assert client.get("/api/me").status_code == 401
    assert client.post("/api/chat", json={"question": "hello"}).status_code == 401
    assert client.get("/history", follow_redirects=False).headers["location"] == "/login"


def test_deleted_user_loses_access(client, registered_user):
    from app.db_connect import SessionLocal
    from app.models.user import User

    assert client.post("/api/login", json=CREDENTIALS).status_code == 200
    with SessionLocal() as db:
        db.delete(db.get(User, registered_user["id"]))
        db.commit()
    assert client.get("/api/me").status_code == 401
    assert client.cookies.get(COOKIE) is None


@pytest.mark.parametrize("path", ["/chat", "/history"])
def test_protected_pages(client, registered_user, path):
    response = client.get(path, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"
    assert client.post("/api/login", json=CREDENTIALS).status_code == 200
    response = client.get(path)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["content-type"].startswith("text/html")
    assert client.get("/login", follow_redirects=False).headers["location"] == "/chat"


def test_unauthenticated_request_never_calls_ai(client, registered_user, monkeypatch):
    from app import llm_connect

    questions = []

    async def answer(question, history):
        questions.append(question)
        return "test answer"

    monkeypatch.setattr(llm_connect, "generate_answer", answer)
    response = client.post("/api/chat", json={"question": "hello", "user_id": registered_user["id"]})
    assert response.status_code == 401
    assert questions == []
    assert client.post("/api/login", json=CREDENTIALS).status_code == 200
    response = client.post("/api/chat", json={"question": "hello"})
    assert response.status_code == 200
    assert response.json() == {"answer": "test answer"}
    assert questions == ["hello"]


@pytest.mark.parametrize("path", ["/api/signup", "/api/login", "/api/logout", "/api/chat"])
@pytest.mark.parametrize("header", [None, "wrong-value"])
def test_post_requires_csrf_header(client, registered_user, path, header):
    assert client.post("/api/login", json=CREDENTIALS).status_code == 200
    client.headers.pop("X-Requested-With")
    headers = {} if header is None else {"X-Requested-With": header}
    response = client.post(path, json={**CREDENTIALS, "question": "hello"}, headers=headers)
    assert response.status_code == 403
    assert "set-cookie" not in response.headers
    assert client.get("/api/me").json() == registered_user


def test_cross_origin_preflight_is_not_allowed(client):
    response = client.options("/api/login", headers={
        "Origin": "https://another.example",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "X-Requested-With, Content-Type",
    })
    assert response.status_code == 405
    assert "access-control-allow-origin" not in response.headers


@pytest.mark.parametrize("operation", ["login", "session"])
def test_db_error_is_not_reported_as_invalid_credentials(client, registered_user, monkeypatch, caplog, operation):
    from app import account, auth

    assert client.post("/api/login", json=CREDENTIALS).status_code == 200

    def fail_lookup(*args):
        raise OperationalError("SELECT users", {}, SQLiteOperationalError("test DB failure"))

    target, name = (account, "get_user_by_username") if operation == "login" else (auth, "get_user_by_id")
    with monkeypatch.context() as patch:
        patch.setattr(target, name, fail_lookup)
        response = client.post("/api/login", json=CREDENTIALS) if operation == "login" else client.get("/api/me")
    assert response.status_code == 500
    assert response.json() == {"detail": "로그인 정보를 확인하지 못했습니다."}
    assert f"db_read_failure operation={operation}" in caplog.text
    assert "test DB failure" not in response.text
    assert PASSWORD not in caplog.text
    assert client.get("/api/me").json() == registered_user


def test_session_survives_app_restart(application, client, registered_user, csrf_headers):
    assert client.post("/api/login", json=CREDENTIALS).status_code == 200
    cookie = client.cookies.get(COOKIE)
    with TestClient(application, headers=csrf_headers) as restarted:
        restarted.cookies.set(COOKIE, cookie)
        assert restarted.get("/api/me").json() == registered_user
