"""계정 DB 작업. 공통 세션을 받아 저장하고 실패하면 rollback한다."""

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.user import User


def create_user(db: Session, username: str, password_hash: str) -> int:
    """사용자를 저장하고 생성된 ID를 반환한다. DB 예외는 호출자에게 전달한다."""
    user = User(username=username, password_hash=password_hash)
    db.add(user)
    try:
        db.flush()
        user_id = user.id
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise
    return user_id
