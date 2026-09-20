"""
   AskMate Backend Project

   파일명   : db_connect.py                                                          
   생성자   : Changhwan Kim

   생성일   : 2026/09/14
   업데이트  : 2026/09/20

   설명     : SQLite 연결, SQLAlchemy 공통 모델 기반과 요청별 세션 제공
"""

from collections.abc import Generator

from sqlalchemy import URL, create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import DATABASE_PATH
from app.logger import logger

engine = create_engine(
    URL.create("sqlite", database=str(DATABASE_PATH)),
    connect_args={"check_same_thread": False},
    hide_parameters=True,  # DB 예외 로그에 비밀번호 해시 등 SQL 인자를 노출하지 않는다.
)
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    """models/에서 테이블을 정의할 때 상속할 공통 기반."""


@event.listens_for(engine, "connect")
def enable_foreign_keys(connection, connection_record):
    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def check_connection() -> None:
    """저장 디렉터리와 DB 파일을 준비하고 연결만 확인한다."""
    try:
        DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        logger.info("db_connection_success")
    except Exception:
        logger.exception("db_connection_failure")
        raise


def get_db() -> Generator[Session, None, None]:
    """각 요청에 독립된 세션을 제공한다. 쓰기 작업의 commit은 호출자가 한다."""
    with SessionLocal() as session:
        yield session


def init_db() -> None:
    """DB 연결을 확인하고 아직 없는 테이블을 생성한다."""
    from app.models import user  # 테이블 정의를 Base.metadata에 등록한다.

    check_connection()
    Base.metadata.create_all(bind=engine)
