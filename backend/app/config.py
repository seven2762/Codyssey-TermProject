"""실행 위치와 관계없이 공통 경로와 환경변수를 읽는다."""

import os
from pathlib import Path

from dotenv import load_dotenv

APP_DIR = Path(__file__).resolve().parent
BACKEND_DIR = APP_DIR.parent

# 배포 환경에서 전달한 값이 로컬 .env보다 우선한다.
load_dotenv(BACKEND_DIR / ".env", override=False)

DATABASE_PATH = Path(os.getenv("DATABASE_PATH", "data/askmate.db"))
if not DATABASE_PATH.is_absolute():
    DATABASE_PATH = BACKEND_DIR / DATABASE_PATH
