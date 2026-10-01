"""
   AskMate Backend Project

   파일명   : history.py                                                          
   생성자   : Changhwan Kim

   생성일   : 2026/09/14
   업데이트  : 2026/09/20

   설명     : 로그인 사용자의 대화 기록 조회 API
"""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.chat_db import get_chats_by_user
from app.db_connect import get_db
from app.logger import logger
from app.models.user import User

router = APIRouter()


class ChatResponse(BaseModel):
    id: int
    question: str
    answer: str
    created_at: datetime


@router.get("/me/chats", response_model=list[ChatResponse])
def get_my_chats(
    response: Response,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[ChatResponse]:
    """본인의 대화 기록을 최신순으로 반환한다. 기록이 없으면 빈 배열을 반환한다."""
    try:
        chats = get_chats_by_user(db, user.id)
    except SQLAlchemyError:
        logger.exception("db_read_failure operation=history user_id=%s", user.id)
        raise HTTPException(status_code=500, detail="대화 기록을 불러오지 못했습니다.") from None

    response.headers["Cache-Control"] = "no-store"
    return [
        ChatResponse(
            id=chat.id,
            question=chat.question,
            answer=chat.answer,
            created_at=chat.created_at.replace(tzinfo=UTC),
        )
        for chat in chats
    ]
