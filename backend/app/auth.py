"""API·화면에서 공유하는 세션 인증과 POST 요청 헤더 검사."""

from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.account_db import get_user_by_id
from app.db_connect import get_db
from app.logger import logger
from app.models.user import User


def require_csrf_header(
    requested_with: Annotated[
        str | None,
        Header(alias="X-Requested-With", description="POST 요청에는 XMLHttpRequest를 지정합니다."),
    ] = None,
) -> None:
    """브라우저의 다른 출처에서 전송한 단순 요청을 차단한다. CORS 허용과 함께 쓰지 않는다."""
    if requested_with != "XMLHttpRequest":
        raise HTTPException(status_code=403, detail="X-Requested-With: XMLHttpRequest 헤더가 필요합니다.")


def get_session_user(request: Request, db: Annotated[Session, Depends(get_db)]) -> User | None:
    """유효한 세션의 사용자를 반환한다. 비로그인 상태라면 None을 반환한다."""
    user_id = request.session.get("user_id")
    if user_id is None:
        return None
    try:
        user = get_user_by_id(db, user_id)
    except SQLAlchemyError:
        logger.exception("db_read_failure operation=session")
        raise HTTPException(status_code=500, detail="로그인 정보를 확인하지 못했습니다.") from None
    if user is None:
        request.session.clear()
    return user


def get_current_user(user: Annotated[User | None, Depends(get_session_user)]) -> User:
    """로그인이 필요한 API에서 사용한다."""
    if user is None:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    return user
