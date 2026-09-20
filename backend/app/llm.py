"""
   AskMate Backend Project

   파일명   : llm.py                                                          
   생성자   : Changhwan Kim

   생성일   : 2026/09/14
   업데이트  : 2026/09/20

   설명     : 로그인 사용자의 AI 질문 처리와 대화 기록 저장
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, StringConstraints
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app import llm_connect
from app.auth import get_current_user, require_csrf_header
from app.chat_db import create_chat
from app.db_connect import get_db
from app.logger import logger
from app.models.user import User

router = APIRouter()


class ChatRequest(BaseModel):
    question: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)
    ]


@router.post("/chat", dependencies=[Depends(require_csrf_header)])
async def chat(
    payload: ChatRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """AI 답변을 받은 뒤 대화 기록을 저장하고 응답한다. 문맥 조회는 후속 구현한다."""
    user_id = user.id
    logger.info("request_received user_id=%s path=/api/chat", user_id)
    try:
        answer = await llm_connect.generate_answer(payload.question, history=[])
    except NotImplementedError:
        raise HTTPException(status_code=501, detail="AI 연결이 아직 구현되지 않았습니다.") from None

    try:
        # 동기 DB 저장이 다른 비동기 요청을 막지 않도록 스레드에서 실행한다.
        chat_id = await run_in_threadpool(create_chat, db, user_id, payload.question, answer)
    except SQLAlchemyError:
        logger.exception("db_save_failure operation=chat user_id=%s", user_id)
        raise HTTPException(status_code=500, detail="대화 기록을 저장하지 못했습니다.") from None
    logger.info("db_save_success operation=chat user_id=%s chat_id=%s", user_id, chat_id)
    return {"answer": answer}
