"""
   AskMate Backend Project

   파일명   : llm.py                                                          
   생성자   : Changhwan Kim

   생성일   : 2026/09/14
   업데이트  : 2026/09/15

   설명     : LLM 연동 API를 추가할 모듈
"""

from typing import Annotated

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, StringConstraints

from app import llm_connect
from app.logger import logger

router = APIRouter()


class ChatRequest(BaseModel):
    question: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=1000)
    ]


@router.post("/chat")
async def chat(payload: ChatRequest):
    """통신 경계만 연결한 골격. 인증·기록 조회·저장은 후속 구현한다."""
    logger.info("request_received path=/api/chat")
    try:
        answer = await llm_connect.generate_answer(payload.question, history=[])
    except NotImplementedError:
        raise HTTPException(status_code=501, detail="AI 연결이 아직 구현되지 않았습니다.") from None
    return {"answer": answer}
