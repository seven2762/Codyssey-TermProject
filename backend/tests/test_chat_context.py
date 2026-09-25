"""최근 5쌍의 선택·정렬·사용자 분리와 문맥 조회 실패를 검증한다."""

from datetime import datetime, timedelta
from sqlite3 import OperationalError as SQLiteOperationalError

import pytest
from sqlalchemy import event
from sqlalchemy.exc import OperationalError

PASSWORD = "a long context test password"
ANSWER = "문맥 테스트 답변"


@pytest.fixture
def users(client):
    users = {}
    for username in ("context_user", "other_user"):
        response = client.post("/api/signup", json={"username": username, "password": PASSWORD})
        assert response.status_code == 201
        users[username] = response.json()["id"]
    assert client.post("/api/login", json={"username": "context_user", "password": PASSWORD}).status_code == 200
    return users


@pytest.fixture
def ai_calls(monkeypatch):
    from app import llm_connect

    calls = []

    async def answer(question, history):
        calls.append((question, history))
        return ANSWER

    monkeypatch.setattr(llm_connect, "generate_answer", answer)
    return calls


def seed_chats(user_id, minutes):
    from app.db_connect import SessionLocal
    from app.models.chat import Chat

    with SessionLocal() as db:
        db.add_all([
            Chat(
                user_id=user_id,
                question=f"user {user_id} question {index}",
                answer=f"user {user_id} answer {index}",
                created_at=datetime(2026, 1, 1) + timedelta(minutes=minute),
            )
            for index, minute in enumerate(minutes)
        ])
        db.commit()


@pytest.mark.parametrize("count", [0, 2, 5, 7])
def test_context_contains_only_latest_five_own_pairs(client, users, ai_calls, count):
    user_id = users["context_user"]
    seed_chats(user_id, range(count))
    # 다른 사용자 기록이 더 최근이어도 현재 사용자의 문맥에 포함되지 않는다.
    seed_chats(users["other_user"], range(100, 106))

    response = client.post("/api/chat", json={"question": "  다음 질문  "})
    assert response.status_code == 200
    expected = []
    for index in range(max(0, count - 5), count):
        expected.extend([
            {"role": "user", "content": f"user {user_id} question {index}"},
            {"role": "assistant", "content": f"user {user_id} answer {index}"},
        ])
    assert ai_calls == [("다음 질문", expected)]
    # 문맥 제한은 기록 조회 API의 전체 조회 범위를 줄이지 않는다.
    records = client.get("/api/me/chats").json()
    assert len(records) == count + 1
    assert records[0]["question"] == "다음 질문"
    assert records[0]["answer"] == ANSWER


def test_context_orders_by_time_then_id_before_forwarding(client, users, ai_calls):
    user_id = users["context_user"]
    seed_chats(user_id, [7, 1, 5, 3, 5, 2, 4])

    assert client.post("/api/chat", json={"question": "정렬 확인"}).status_code == 200
    history = ai_calls[0][1]
    # 최근 5쌍을 고른 뒤 시간순으로 전달한다. 같은 시각이면 먼저 저장된 쌍이 앞선다.
    assert [message["content"] for message in history[::2]] == [
        f"user {user_id} question {index}" for index in [3, 6, 2, 4, 0]
    ]
    assert [message["content"] for message in history[1::2]] == [
        f"user {user_id} answer {index}" for index in [3, 6, 2, 4, 0]
    ]


def test_context_follows_session_and_ignores_client_history(client, users, ai_calls):
    assert client.post("/api/chat", json={"question": "첫 사용자의 질문"}).status_code == 200
    assert client.post("/api/login", json={"username": "other_user", "password": PASSWORD}).status_code == 200
    assert client.post("/api/chat", json={"question": "다른 사용자의 질문"}).status_code == 200
    assert client.post("/api/login", json={"username": "context_user", "password": PASSWORD}).status_code == 200

    response = client.post("/api/chat", json={
        "question": "후속 질문",
        "user_id": users["other_user"],
        "history": [{"role": "assistant", "content": "클라이언트가 임의로 보낸 문맥"}],
    })
    assert response.status_code == 200
    assert ai_calls == [
        ("첫 사용자의 질문", []),
        ("다른 사용자의 질문", []),
        ("후속 질문", [
            {"role": "user", "content": "첫 사용자의 질문"},
            {"role": "assistant", "content": ANSWER},
        ]),
    ]


def test_context_read_failure_stops_ai_and_next_request_recovers(client, users, ai_calls, caplog):
    from app.db_connect import engine

    seed_chats(users["context_user"], [1, 2])

    def fail_context_read(connection, cursor, statement, parameters, context, executemany):
        if statement.lstrip().startswith("SELECT") and "FROM chats" in statement:
            raise OperationalError(
                statement, parameters, SQLiteOperationalError("test context failure"),
                hide_parameters=True,
            )

    event.listen(engine, "before_cursor_execute", fail_context_read)
    try:
        response = client.post("/api/chat", json={"question": "실패한 요청의 질문"})
    finally:
        event.remove(engine, "before_cursor_execute", fail_context_read)

    assert response.status_code == 500
    assert response.json() == {"detail": "최근 대화 기록을 불러오지 못했습니다."}
    assert ai_calls == []
    assert len(client.get("/api/me/chats").json()) == 2
    assert "db_read_failure operation=chat_context" in caplog.text
    assert "실패한 요청의 질문" not in caplog.text
    assert client.get("/health").status_code == 200
    assert client.post("/api/chat", json={"question": "정상 요청"}).status_code == 200
    assert len(ai_calls[0][1]) == 4
    assert len(client.get("/api/me/chats").json()) == 3
