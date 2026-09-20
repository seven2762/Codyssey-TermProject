"""
   AskMate Backend Project

   파일명   : account.py                                                          
   생성자   : Changhwan Kim

   생성일   : 2026/09/14
   업데이트  : 2026/09/20

   설명     : 회원가입·로그인·로그아웃과 현재 사용자 API
"""

from sqlite3 import SQLITE_CONSTRAINT_UNIQUE
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, SecretStr, StringConstraints
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.account_db import create_user, get_user_by_username
from app.auth import get_current_user, require_csrf_header
from app.db_connect import get_db
from app.logger import logger
from app.models.user import User
from app.security import hash_password, verify_password

router = APIRouter()


type Username = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        to_lower=True,
        min_length=3,
        max_length=30,
        pattern=r"^[a-zA-Z0-9_]+$",
    ),
]


class SignUpPayload(BaseModel):
    username: Username
    password: Annotated[SecretStr, Field(min_length=15, max_length=128)]


class LoginPayload(BaseModel):
    username: Username
    # 가입 시의 최소 길이 정책과 분리하고, 비밀번호를 변환하지 않는다.
    password: Annotated[SecretStr, Field(min_length=1, max_length=128)]


class UserResponse(BaseModel):
    id: int
    username: str


@router.post(
    "/signup", status_code=201, response_model=UserResponse,
    dependencies=[Depends(require_csrf_header)],
)
def signup(payload: SignUpPayload, db: Annotated[Session, Depends(get_db)]) -> UserResponse:
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
    return UserResponse(id=user_id, username=payload.username)


@router.post("/login", response_model=UserResponse, dependencies=[Depends(require_csrf_header)])
def login(
    payload: LoginPayload,
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
) -> UserResponse:
    """비밀번호를 검증하고 현재 브라우저에 로그인 세션을 발급한다."""
    logger.info("request_received path=/api/login")
    try:
        user = get_user_by_username(db, payload.username)
    except SQLAlchemyError:
        logger.exception("db_read_failure operation=login")
        raise HTTPException(status_code=500, detail="로그인 정보를 확인하지 못했습니다.") from None
    if user is None or not verify_password(payload.password.get_secret_value(), user.password_hash):
        logger.warning("login_failure")
        raise HTTPException(status_code=401, detail="사용자명 또는 비밀번호가 올바르지 않습니다.")

    request.session.clear()
    request.session["user_id"] = user.id
    response.headers["Cache-Control"] = "no-store"
    logger.info("login_success user_id=%s", user.id)
    return UserResponse(id=user.id, username=user.username)


@router.get("/me", response_model=UserResponse)
def me(response: Response, user: Annotated[User, Depends(get_current_user)]) -> UserResponse:
    """현재 로그인한 사용자의 공개 정보만 반환한다."""
    response.headers["Cache-Control"] = "no-store"
    return UserResponse(id=user.id, username=user.username)


@router.post("/logout", status_code=204, dependencies=[Depends(require_csrf_header)])
def logout(request: Request) -> Response:
    """현재 브라우저의 세션을 비운다. 이미 비로그인 상태여도 성공한다."""
    logger.info("request_received path=/api/logout")
    user_id = request.session.get("user_id")
    request.session.clear()
    logger.info("logout_success user_id=%s", user_id)
    return Response(status_code=204, headers={"Cache-Control": "no-store"})
