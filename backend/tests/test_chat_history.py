"""본인 기록 조회, 최신순 정렬, UTC 응답과 조회 실패 처리를 임시 DB로 검증한다."""

from datetime import UTC, datetime
from pathlib import Path
import sqlite3

from fastapi.testclient import TestClient
from itsdangerous import TimestampSigner
import pytest
from sqlalchemy import event
from sqlalchemy.exc import OperationalError

PASSWORD = "a long history password"
COOKIE = "askmate_session"


@pytest.fixture
def users(client):
    result = {}
    for username in ("history_user", "another_user", "empty_user"):
        response = client.post("/api/signup", json={"username": username, "password": PASSWORD})
        assert response.status_code == 201
        result[username] = response.json()["id"]
    assert client.post("/api/login", json={"username": "history_user", "password": PASSWORD}).status_code == 200
    return result


@pytest.fixture
def records(client, users):
    from app.db_connect import SessionLocal
    from app.models.chat import Chat

    with SessionLocal() as db:
        db.add_all([
            Chat(user_id=users["history_user"], question="새 질문", answer="새 답변",
                 created_at=datetime(2026, 9, 20, 3, 0, 0, 123456)),
            Chat(user_id=users["history_user"], question="이전 질문", answer="이전 답변",
                 created_at=datetime(2026, 9, 19, 3, 0)),
            Chat(user_id=users["history_user"], question="같은 시각의 질문", answer="같은 시각의 답변",
                 created_at=datetime(2026, 9, 20, 3, 0, 0, 123456)),
            Chat(user_id=users["another_user"], question="다른 사용자의 질문", answer="다른 사용자의 답변",
                 created_at=datetime(2026, 9, 21, 3, 0)),
        ])
        db.commit()


def test_history_returns_only_own_records_in_stable_latest_order(client, records, caplog):
    response = client.get("/api/me/chats")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == [
        {"id": 3, "question": "같은 시각의 질문", "answer": "같은 시각의 답변", "created_at": "2026-09-20T03:00:00.123456Z"},
        {"id": 1, "question": "새 질문", "answer": "새 답변", "created_at": "2026-09-20T03:00:00.123456Z"},
        {"id": 2, "question": "이전 질문", "answer": "이전 답변", "created_at": "2026-09-19T03:00:00Z"},
    ]
    assert "set-cookie" not in response.headers
    for record in response.json():
        assert record["question"] not in caplog.text
        assert record["answer"] not in caplog.text


def test_query_user_id_cannot_change_record_owner(client, users, records):
    response = client.get("/api/me/chats", params={"user_id": users["another_user"]})
    assert response.status_code == 200
    assert [record["id"] for record in response.json()] == [3, 1, 2]
    assert client.post("/api/login", json={"username": "another_user", "password": PASSWORD}).status_code == 200
    response = client.get("/api/me/chats", params={"user_id": users["history_user"]})
    assert [record["id"] for record in response.json()] == [4]


def test_user_without_records_gets_empty_array_without_post_header(client, records):
    assert client.post("/api/login", json={"username": "empty_user", "password": PASSWORD}).status_code == 200
    client.headers.pop("X-Requested-With")
    response = client.get("/api/me/chats")
    assert response.status_code == 200
    assert response.json() == []
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("state", ["anonymous", "logged_out", "tampered", "expired"])
def test_invalid_session_cannot_read_records(client, records, monkeypatch, state):
    if state == "anonymous":
        client.cookies.clear()
    elif state == "logged_out":
        assert client.post("/api/logout").status_code == 204
    elif state == "tampered":
        cookie = client.cookies.get(COOKIE)
        client.cookies.clear()
        client.cookies.set(COOKIE, cookie + "invalid")
    else:
        now = TimestampSigner.get_timestamp
        monkeypatch.setattr(TimestampSigner, "get_timestamp", lambda self: now(self) + 3601)
    response = client.get("/api/me/chats")
    assert response.status_code == 401
    assert response.json() == {"detail": "로그인이 필요합니다."}


def test_query_failure_returns_500_and_next_request_recovers(client, records, caplog):
    from app.db_connect import engine

    def fail_read(connection, cursor, statement, parameters, context, executemany):
        if "FROM chats" in statement:
            raise OperationalError(statement, parameters, sqlite3.OperationalError("test read failure"), hide_parameters=True)

    event.listen(engine, "before_cursor_execute", fail_read)
    try:
        response = client.get("/api/me/chats")
    finally:
        event.remove(engine, "before_cursor_execute", fail_read)
    assert response.status_code == 500
    assert response.json() == {"detail": "대화 기록을 불러오지 못했습니다."}
    assert "db_read_failure operation=history" in caplog.text
    assert "test read failure" not in response.text
    assert "같은 시각의 질문" not in caplog.text
    assert "같은 시각의 답변" not in caplog.text
    recovered = client.get("/api/me/chats")
    assert recovered.status_code == 200
    assert len(recovered.json()) == 3


def test_saved_chat_is_visible_through_history_api(client, users, monkeypatch):
    from app import llm_connect

    async def answer(question, history):
        return "저장 후 조회할 답변\n두 번째 줄"

    monkeypatch.setattr(llm_connect, "generate_answer", answer)
    saved = client.post("/api/chat", json={"question": "  저장 후 조회할 질문  "})
    assert saved.status_code == 200
    response = client.get("/api/me/chats")
    assert response.status_code == 200
    record, = response.json()
    assert record["question"] == "저장 후 조회할 질문"
    assert record["answer"] == saved.json()["answer"]
    assert datetime.fromisoformat(record["created_at"]).tzinfo is UTC


def test_records_can_be_read_after_app_restart(application, client, records):
    before = client.get("/api/me/chats").json()
    with TestClient(application) as restarted:
        restarted.cookies.set(COOKIE, client.cookies.get(COOKIE))
        response = restarted.get("/api/me/chats")
        assert response.status_code == 200
        assert response.json() == before


def test_verification_sql_filters_users_and_matches_api_order(client, users, records):
    from app.config import DATABASE_PATH

    query = (Path(__file__).resolve().parents[1] / "scripts/check_logs.sql").read_text()
    with sqlite3.connect(DATABASE_PATH) as connection:
        for username, expected_ids in [("history_user", [3, 1, 2]), ("another_user", [4]), ("empty_user", [])]:
            rows = connection.execute(query, {"user_id": users[username]}).fetchall()
            assert [row[0] for row in rows] == expected_ids
            assert all(row[1] == users[username] for row in rows)


def test_history_openapi_documents_array_and_datetime(client):
    schema = client.get("/openapi.json").json()
    operation = schema["paths"]["/api/me/chats"]["get"]
    response = operation["responses"]["200"]["content"]["application/json"]["schema"]
    assert response["type"] == "array"
    model_name = response["items"]["$ref"].split("/")[-1]
    model = schema["components"]["schemas"][model_name]
    assert set(model["required"]) == {"id", "question", "answer", "created_at"}
    assert model["properties"]["created_at"]["format"] == "date-time"
    assert not any(parameter["name"] == "user_id" for parameter in operation.get("parameters", []))
