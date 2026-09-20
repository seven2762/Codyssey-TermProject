"""대화 기록 저장·조회. DB 예외는 호출자에게 전달한다."""

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.chat import Chat


def create_chat(db: Session, user_id: int, question: str, answer: str) -> int:
    """질문·답변 한 쌍을 저장하고 생성된 기록 ID를 반환한다."""
    chat = Chat(user_id=user_id, question=question, answer=answer)
    db.add(chat)
    try:
        db.flush()
        chat_id = chat.id
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    return chat_id


def get_chats_by_user(db: Session, user_id: int) -> list[Chat]:
    """해당 사용자의 대화 기록을 생성 시각·ID 내림차순으로 조회한다."""
    statement = (
        select(Chat)
        .where(Chat.user_id == user_id)
        .order_by(Chat.created_at.desc(), Chat.id.desc())
    )
    return list(db.scalars(statement))
