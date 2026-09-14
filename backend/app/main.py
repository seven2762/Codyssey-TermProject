"""
   AskMate Backend Project

   파일명   : main.py                                                          
   생성자   : Changhwan Kim

   생성일   : 2026/09/14
   업데이트  : 2026/09/14

   설명     : FastAPI 서버 설정 및 AI 채팅 및 채팅 기록 관리 라우터 포함                  
"""

# 파이썬 모듈
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI

# 자체 제작 모듈
from app.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    server_start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info("------------------------------------------------------------")
    logger.info(f"AskMate Backend Server started at {server_start_time}")
    logger.info("------------------------------------------------------------")
    yield


app = FastAPI(title="AskMate", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
