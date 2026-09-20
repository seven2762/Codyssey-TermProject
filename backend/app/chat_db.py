"""대화 기록 저장. DB 예외는 호출자에게 전달한다."""

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
