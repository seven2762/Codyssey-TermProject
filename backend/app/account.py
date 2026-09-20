"""
   AskMate Backend Project

   파일명   : account.py                                                          
   생성자   : Changhwan Kim

   생성일   : 2026/09/14
   업데이트  : 2026/09/20

   설명     : 회원가입 요청 검증과 계정 API
"""

from sqlite3 import SQLITE_CONSTRAINT_UNIQUE
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, SecretStr, StringConstraints
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.account_db import create_user
from app.db_connect import get_db
from app.logger import logger
from app.security import hash_password

router = APIRouter()


class SignUpPayload(BaseModel):
    username: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True,
            to_lower=True,
            min_length=3,
            max_length=30,
            pattern=r"^[a-zA-Z0-9_]+$",
        ),
    ]
    password: Annotated[SecretStr, Field(min_length=15, max_length=128)]


class SignUpResponse(BaseModel):
    id: int
    username: str


@router.post("/signup", status_code=201, response_model=SignUpResponse)
def signup(payload: SignUpPayload, db: Annotated[Session, Depends(get_db)]) -> SignUpResponse:
    """사용자를 생성한다. 로그인과 세션 발급은 별도 API에서 처리한다."""
    logger.info("request_received path=/api/signup")
    password_hash = hash_password(payload.password.get_secret_value())
    try:
        user_id = create_user(db, payload.username, password_hash)
    except SQLAlchemyError as exc:
        if (
            isinstance(exc, IntegrityError)
            and exc.orig.sqlite_errorcode == SQLITE_CONSTRAINT_UNIQUE
        ):
            logger.warning("signup_duplicate_username")
            raise HTTPException(status_code=409, detail="이미 사용 중인 사용자명입니다.") from None
        logger.exception("db_save_failure operation=signup")
        raise HTTPException(status_code=500, detail="회원가입 정보를 저장하지 못했습니다.") from None

    logger.info("db_save_success operation=signup user_id=%s", user_id)
    return SignUpResponse(id=user_id, username=payload.username)
