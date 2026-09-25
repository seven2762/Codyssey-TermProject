"""
   AskMate Backend Project

   파일명   : main.py                                                          
   생성자   : Changhwan Kim

   생성일   : 2026/09/14
   업데이트  : 2026/09/20

   설명     : FastAPI 서버 설정 및 AI 채팅 및 채팅 기록 관리 라우터 포함                  
"""

# 파이썬 모듈
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

# 자체 제작 모듈
from app.logger import logger
from app.config import APP_DIR, SESSION_HTTPS_ONLY, SESSION_MAX_AGE, SESSION_SECRET_KEY
from app.db_connect import engine, init_db

# 앱 라우터
from app.account import router as account_router
from app.history import router as history_router
from app.llm import router as llm_router
from app.pages import router as pages_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    server_start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info("------------------------------------------------------------")
    logger.info(f"AskMate Backend Server started at {server_start_time}")
    logger.info("------------------------------------------------------------")
    try:
        yield
    finally:
        engine.dispose()


app = FastAPI(title="AskMate", lifespan=lifespan)
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET_KEY,
    session_cookie="askmate_session",
    max_age=SESSION_MAX_AGE,
    same_site="lax",
    https_only=SESSION_HTTPS_ONLY,
)
app.mount("/static", StaticFiles(directory=str(APP_DIR / "static")), name="static")
app.include_router(pages_router)
app.include_router(account_router, prefix="/api")
app.include_router(llm_router, prefix="/api")
app.include_router(history_router, prefix="/api")


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    # 원본 입력(input, ctx)에 포함될 수 있는 비밀번호를 응답에서 제외한다.
    errors = [
        {"type": error["type"], "loc": error["loc"], "msg": error["msg"]}
        for error in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": errors})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
