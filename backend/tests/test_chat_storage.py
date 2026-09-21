"""대화 저장과 실패 시 rollback을 임시 SQLite 및 테스트용 AI 응답으로 검증한다."""

from datetime import UTC, datetime
import os
from pathlib import Path
from sqlite3 import OperationalError as SQLiteOperationalError
import subprocess
import sys

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

PASSWORD = "a long password phrase"
ANSWER = "테스트 답변입니다.\n두 번째 줄도 그대로 저장합니다."


@pytest.fixture
def logged_in_user(client):
    credentials = {"username": "chat_user", "password": PASSWORD}
    response = client.post("/api/signup", json=credentials)
    assert response.status_code == 201
    assert client.post("/api/login", json=credentials).status_code == 200
    return response.json()


@pytest.fixture
def ai_calls(monkeypatch):
    from app import llm_connect

    calls = []

    async def answer(question, history):
        calls.append((question, history))
        return ANSWER

    monkeypatch.setattr(llm_connect, "generate_answer", answer)
    return calls


def read_chats():
    from app.db_connect import SessionLocal
    from app.models.chat import Chat

    with SessionLocal() as db:
        return db.scalars(select(Chat).order_by(Chat.id)).all()


def test_chat_saves_question_answer_and_utc_time(client, logged_in_user, ai_calls, caplog):
    caplog.set_level("INFO")
    for question in ("  첫 질문입니다.\n다음 줄  ", "질" * 1000):
        response = client.post("/api/chat", json={"question": question})
        assert response.status_code == 200
        assert response.json() == {"answer": ANSWER}

    chats = read_chats()
    assert len(chats) == 2
    assert [chat.question for chat in chats] == ["첫 질문입니다.\n다음 줄", "질" * 1000]
    assert ai_calls == [
        (chats[0].question, []),
        (chats[1].question, [
            {"role": "user", "content": chats[0].question},
            {"role": "assistant", "content": ANSWER},
        ]),
    ]
    for chat in chats:
        assert chat.user_id == logged_in_user["id"]
        assert chat.answer == ANSWER
        assert chat.created_at.tzinfo is None
        assert abs((datetime.now(UTC) - chat.created_at.replace(tzinfo=UTC)).total_seconds()) < 60
        assert f"db_save_success operation=chat user_id={chat.user_id} chat_id={chat.id}" in caplog.text
        assert chat.question not in caplog.text
    assert ANSWER not in caplog.text
    assert PASSWORD not in caplog.text


def test_chat_owner_comes_from_session(client, logged_in_user, ai_calls):
    other_credentials = {"username": "another_user", "password": PASSWORD}
    response = client.post("/api/signup", json=other_credentials)
    assert response.status_code == 201
    other_id = response.json()["id"]

    response = client.post("/api/chat", json={"question": "첫 사용자", "user_id": other_id})
    assert response.status_code == 200
    assert client.post("/api/login", json=other_credentials).status_code == 200
    response = client.post("/api/chat", json={"question": "다른 사용자", "user_id": logged_in_user["id"]})
    assert response.status_code == 200
    assert [(chat.user_id, chat.question) for chat in read_chats()] == [
        (logged_in_user["id"], "첫 사용자"),
        (other_id, "다른 사용자"),
    ]


@pytest.mark.parametrize(
    "case, question, status",
    [("logout", "hello", 401), ("missing_header", "hello", 403),
     ("empty", " \n ", 422), ("too_long", "질" * 1001, 422)],
)
def test_rejected_request_does_not_call_ai_or_save(client, logged_in_user, ai_calls, case, question, status):
    if case == "logout":
        assert client.post("/api/logout").status_code == 204
    elif case == "missing_header":
        client.headers.pop("X-Requested-With")
    assert client.post("/api/chat", json={"question": question}).status_code == status
    assert ai_calls == []
    assert read_chats() == []


def test_unreachable_ai_does_not_save(client, logged_in_user):
    """테스트 설정의 AI_BASE_URL은 해석되지 않으므로 연결 실패로 502가 된다."""
    assert client.post("/api/chat", json={"question": "hello"}).status_code == 502
    assert read_chats() == []


@pytest.mark.parametrize(
    "error_name, status",
    [("AITimeoutError", 504), ("AIServiceError", 502)],
)
def test_ai_failure_does_not_save(client, logged_in_user, monkeypatch, error_name, status):
    from app import llm_connect

    error_type = getattr(llm_connect, error_name)

    async def fail(question, history):
        raise error_type("test AI failure")

    monkeypatch.setattr(llm_connect, "generate_answer", fail)
    assert client.post("/api/chat", json={"question": "hello"}).status_code == status
    assert read_chats() == []


def test_unexpected_ai_error_does_not_save(client, logged_in_user, monkeypatch):
    """AIError가 아닌 예외는 삼키지 않는다. 저장은 하지 않아야 한다."""
    from app import llm_connect

    async def fail(question, history):
        raise RuntimeError("test AI failure")

    monkeypatch.setattr(llm_connect, "generate_answer", fail)
    with pytest.raises(RuntimeError, match="test AI failure"):
        client.post("/api/chat", json={"question": "hello"})
    assert read_chats() == []


def test_foreign_key_failure_rolls_back_and_session_can_be_reused(client, logged_in_user):
    from app.chat_db import create_chat
    from app.db_connect import SessionLocal

    with SessionLocal() as db:
        with pytest.raises(IntegrityError):
            create_chat(db, logged_in_user["id"] + 100, "question", ANSWER)
        assert not db.in_transaction()
        assert read_chats() == []
        chat_id = create_chat(db, logged_in_user["id"], "valid question", ANSWER)
    assert [chat.id for chat in read_chats()] == [chat_id]


def test_constraint_failure_returns_500_without_question(client, logged_in_user, monkeypatch, caplog):
    from app import llm_connect

    async def invalid_answer(question, history):
        return None

    monkeypatch.setattr(llm_connect, "generate_answer", invalid_answer)
    question = "로그에 남기지 않을 질문 내용"
    response = client.post("/api/chat", json={"question": question})
    assert response.status_code == 500
    assert response.json() == {"detail": "대화 기록을 저장하지 못했습니다."}
    assert read_chats() == []
    assert "db_save_failure operation=chat" in caplog.text
    assert "SQL parameters hidden" in caplog.text
    assert question not in caplog.text
    assert "INSERT" not in response.text


def test_commit_failure_rolls_back_and_next_chat_works(client, logged_in_user, ai_calls, monkeypatch, caplog):
    caplog.set_level("INFO")

    def fail_commit(db):
        raise OperationalError("COMMIT", {}, SQLiteOperationalError("test commit failure"))

    with monkeypatch.context() as patch:
        patch.setattr(Session, "commit", fail_commit)
        response = client.post("/api/chat", json={"question": "failed question"})
    assert response.status_code == 500
    assert response.json() == {"detail": "대화 기록을 저장하지 못했습니다."}
    assert read_chats() == []
    assert "db_save_failure operation=chat" in caplog.text
    assert "db_save_success operation=chat" not in caplog.text

    assert client.post("/api/chat", json={"question": "next question"}).status_code == 200
    assert [chat.question for chat in read_chats()] == ["next question"]
    assert ai_calls == [("failed question", []), ("next question", [])]


def test_existing_user_db_gets_chats_and_records_survive_restart(application, tmp_path):
    env = {
        **os.environ,
        "DATABASE_PATH": str(tmp_path / "upgrade.db"),
        "PYTHONPATH": str(Path(__file__).resolve().parents[1]),
    }
    setup = """
from app.db_connect import engine
from app.models.user import User

# 이전 버전처럼 users 테이블만 있는 DB를 만든다.
User.__table__.create(engine)
with engine.begin() as connection:
    connection.execute(User.__table__.insert().values(username='existing', password_hash='test hash'))

from app.db_connect import init_db, SessionLocal
from app.chat_db import create_chat
init_db()
with SessionLocal() as db:
    assert create_chat(db, 1, 'saved question', 'saved answer') == 1
engine.dispose()
"""
    restarted = """
from sqlalchemy import inspect, select
from app.db_connect import engine, init_db, SessionLocal
from app.models.chat import Chat
from app.models.user import User

init_db()
assert set(inspect(engine).get_table_names()) == {'users', 'chats'}
assert any(index['column_names'] == ['user_id'] for index in inspect(engine).get_indexes('chats'))
with SessionLocal() as db:
    assert db.get(User, 1).username == 'existing'
    chats = db.scalars(select(Chat)).all()
    assert len(chats) == 1
    assert (chats[0].user_id, chats[0].question, chats[0].answer) == (1, 'saved question', 'saved answer')
engine.dispose()
"""
    for code in (setup, restarted):
        result = subprocess.run(
            [sys.executable, "-c", code], cwd=tmp_path, env=env,
            text=True, capture_output=True, timeout=30,
        )
        assert result.returncode == 0, result.stderr
