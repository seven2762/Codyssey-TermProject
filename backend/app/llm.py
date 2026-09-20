"""
   AskMate Backend Project

   파일명   : llm.py                                                          
   생성자   : Changhwan Kim

   생성일   : 2026/09/14
   업데이트  : 2026/09/15

   설명     : LLM 연동 API를 추가할 모듈
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, StringConstraints

from app import llm_connect
from app.auth import get_current_user, require_csrf_header
from app.logger import logger
from app.models.user import User

router = APIRouter()


class ChatRequest(BaseModel):
    question: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)
    ]


@router.post("/chat", dependencies=[Depends(require_csrf_header)])
async def chat(payload: ChatRequest, user: Annotated[User, Depends(get_current_user)]):
    """로그인한 사용자만 AI 연결을 호출한다. 기록 조회·저장은 후속 구현한다."""
    logger.info("request_received user_id=%s path=/api/chat", user.id)
    try:
        answer = await llm_connect.generate_answer(payload.question, history=[])
    except NotImplementedError:
        raise HTTPException(status_code=501, detail="AI 연결이 아직 구현되지 않았습니다.") from None
    return {"answer": answer}
