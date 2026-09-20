"""계정 DB 저장·조회. DB 예외는 호출자에게 전달한다."""

from sqlalchemy import select
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


def get_user_by_username(db: Session, username: str) -> User | None:
    """정규화된 사용자명으로 계정을 조회한다."""
    return db.scalar(select(User).where(User.username == username))


def get_user_by_id(db: Session, user_id: int) -> User | None:
    """세션에 저장된 ID로 계정을 조회한다."""
    return db.get(User, user_id)
