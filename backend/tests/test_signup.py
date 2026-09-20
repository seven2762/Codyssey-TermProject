"""회원가입 검증. DB와 로그는 pytest의 임시 디렉터리에서만 생성한다."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from sqlite3 import OperationalError as SQLiteOperationalError
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

PASSWORD = "  a long password phrase  "


def read_users():
    from app.db_connect import SessionLocal
    from app.models.user import User

    with SessionLocal() as db:
        return db.scalars(select(User).order_by(User.id)).all()


def test_signup_saves_user_with_random_salt(client, caplog):
    from app.security import password_hasher

    caplog.set_level("INFO")
    response = client.post("/api/signup", json={"username": " Charles_1 ", "password": PASSWORD})
    assert response.status_code == 201
    assert response.json() == {"id": 1, "username": "charles_1"}
    assert "set-cookie" not in response.headers

    assert client.post("/api/signup", json={"username": "another", "password": PASSWORD}).status_code == 201
    first, second = read_users()
    assert first.password_hash.startswith("$argon2id$")
    assert first.password_hash != second.password_hash
    assert password_hasher.verify(PASSWORD, first.password_hash)
    assert not password_hasher.verify(PASSWORD.strip(), first.password_hash)
    assert abs((datetime.now(UTC) - first.created_at.replace(tzinfo=UTC)).total_seconds()) < 60
    assert "db_save_success operation=signup" in caplog.text
    assert PASSWORD not in caplog.text
    assert first.password_hash not in caplog.text


@pytest.mark.parametrize("password", ["p" * 15, "p" * 128, "긴 비밀번호 문장입니다 반갑습니다"])
def test_password_boundaries(client, password):
    response = client.post("/api/signup", json={"username": "valid_user", "password": password})
    assert response.status_code == 201


@pytest.mark.parametrize(
    "payload",
    [
        {"password": PASSWORD},
        {"username": "valid_user"},
        {"username": "ab", "password": PASSWORD},
        {"username": "a" * 31, "password": PASSWORD},
        {"username": "   ", "password": PASSWORD},
        {"username": "has space", "password": PASSWORD},
        {"username": "invalid!", "password": PASSWORD},
        {"username": "valid_user", "password": "p" * 14},
        {"username": "valid_user", "password": "p" * 129},
        {"username": "valid_user", "password": 123456789012345},
        {"username": "valid_user", "password": {"secret": PASSWORD}},
        [PASSWORD],
    ],
)
def test_invalid_input_is_not_saved_or_echoed(client, payload):
    response = client.post("/api/signup", json=payload)
    assert response.status_code == 422
    assert PASSWORD not in response.text
    assert all(set(error) == {"type", "loc", "msg"} for error in response.json()["detail"])
    assert read_users() == []


def test_duplicate_username_is_case_insensitive(client):
    assert client.post("/api/signup", json={"username": "charles", "password": PASSWORD}).status_code == 201
    response = client.post("/api/signup", json={"username": " CHARLES ", "password": PASSWORD})
    assert response.status_code == 409
    assert response.json() == {"detail": "이미 사용 중인 사용자명입니다."}
    assert len(read_users()) == 1


def test_concurrent_signup_creates_one_user(client):
    barrier = Barrier(2)

    def signup():
        barrier.wait(timeout=10)
        return client.post("/api/signup", json={"username": "same_user", "password": PASSWORD}).status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = [executor.submit(signup) for _ in range(2)]
        assert sorted(result.result(timeout=15) for result in results) == [201, 409]
    assert len(read_users()) == 1


def test_duplicate_rolls_back_and_session_can_be_reused(client):
    from app.account_db import create_user
    from app.db_connect import SessionLocal
    from app.security import hash_password

    password_hash = hash_password(PASSWORD)
    with SessionLocal() as db:
        create_user(db, "original", password_hash)
        with pytest.raises(IntegrityError):
            create_user(db, "original", password_hash)
        assert not db.in_transaction()
        create_user(db, "next_user", password_hash)
    assert len(read_users()) == 2


def test_non_unique_constraint_error_returns_500_without_hash(client, caplog):
    from app.models.user import User

    def invalidate_username(session, flush_context, instances):
        for user in session.new:
            if isinstance(user, User):
                user.username = None

    event.listen(Session, "before_flush", invalidate_username)
    try:
        response = client.post("/api/signup", json={"username": "valid_user", "password": PASSWORD})
    finally:
        event.remove(Session, "before_flush", invalidate_username)

    assert response.status_code == 500
    assert response.json() == {"detail": "회원가입 정보를 저장하지 못했습니다."}
    assert read_users() == []
    assert "db_save_failure operation=signup" in caplog.text
    assert "SQL parameters hidden" in caplog.text
    assert "$argon2" not in caplog.text
    assert PASSWORD not in caplog.text


def test_commit_failure_rolls_back_and_next_signup_works(client):
    def fail_commit(session):
        raise OperationalError("COMMIT", {}, SQLiteOperationalError("test failure"))

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(Session, "commit", fail_commit)
        response = client.post("/api/signup", json={"username": "valid_user", "password": PASSWORD})
    assert response.status_code == 500
    assert read_users() == []
    assert client.post("/api/signup", json={"username": "valid_user", "password": PASSWORD}).status_code == 201


def test_users_survive_app_restart(application, csrf_headers):
    with TestClient(application, headers=csrf_headers) as client:
        response = client.post("/api/signup", json={"username": "persistent", "password": PASSWORD})
        assert response.status_code == 201
        user_id = response.json()["id"]
    with TestClient(application) as restarted:
        assert restarted.get("/health").json() == {"status": "ok"}
        assert any(user.id == user_id and user.username == "persistent" for user in read_users())


def test_existing_pages_and_chat_validation(client):
    for path in ["/health", "/docs", "/openapi.json", "/signup", "/static/css/style.css"]:
        assert client.get(path).status_code == 200
    assert client.post("/api/chat", json={"question": "hello"}).status_code == 501
    assert client.post("/api/chat", json={"question": " "}).status_code == 422
