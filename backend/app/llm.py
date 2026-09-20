"""
   AskMate Backend Project

   파일명   : llm.py                                                          
   생성자   : Changhwan Kim

   생성일   : 2026/09/14
   업데이트  : 2026/09/20

   설명     : 로그인 사용자의 AI 질문 처리와 대화 기록 저장

   역할 분담
   - A: 인증·입력 검증, 최근 문맥 조회, 대화 저장, HTTP 응답 및 요청·DB 로그.
   - B: llm_connect.py의 AI 통신을 구현하고, 이 파일에 통신 예외의 HTTP 변환을 연결한다.
     타임아웃은 504, AI 호출 실패는 502와 사용자용 안내 메시지로 반환한다.
   - AI 키·모델·타임아웃 설정과 AI 호출·성공·실패 로그는 B의 통신 모듈에서 담당한다.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, StringConstraints
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app import llm_connect
from app.auth import get_current_user, require_csrf_header
from app.chat_db import create_chat, get_recent_chats_by_user
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
    """최근 5쌍을 문맥으로 전달하고, AI 답변과 이번 질문을 저장한 뒤 응답한다."""
    user_id = user.id
    logger.info("request_received user_id=%s path=/api/chat", user_id)
    try:
        chats = await run_in_threadpool(get_recent_chats_by_user, db, user_id)
    except SQLAlchemyError:
        logger.exception("db_read_failure operation=chat_context user_id=%s", user_id)
        raise HTTPException(status_code=500, detail="최근 대화 기록을 불러오지 못했습니다.") from None

    history: list[dict[str, str]] = []
    for chat in chats:
        history.extend([
            {"role": "user", "content": chat.question},
            {"role": "assistant", "content": chat.answer},
        ])

    # B 연동 작업: 통신 모듈의 타임아웃·호출 실패 예외를 여기서 HTTP 504·502로 변환한다.
    # 현재는 AI 미구현 상태의 501만 처리한다. 기존 문맥 조회·저장 흐름은 유지한다.
    try:
        answer = await llm_connect.generate_answer(payload.question, history=history)
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
