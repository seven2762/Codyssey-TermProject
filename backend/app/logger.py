"""                                                          
   AskMate Backend Project
                                                                              
   파일명   : logger.py
   생성자   : Changhwan Kim                                
                                                                              
   생성일   : 2026/09/14
   업데이트  : 2026/09/25
                                                                             
   설명     : 디버깅 관련 로깅 함수 정의
"""

import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("app.log", encoding="utf-8"),
    ],
)

logger = logging.getLogger("project_logger")

# B 담당: AI 통신에 쓰는 HTTP 클라이언트는 루트의 DEBUG 설정에서 연결 단계까지 모두 기록해
# 서비스 로그를 덮는다. 요청 한 줄만 남기고 내부 동작은 경고부터 기록한다.
# 질문·답변·Authorization 헤더는 애플리케이션 로그에 직접 기록하지 않는다.
# httpx2·httpcore2는 이 프로젝트가 설치한 배포판 이름이다.
for name in ("httpx", "httpx2", "openai"):
    logging.getLogger(name).setLevel(logging.INFO)
for name in ("httpcore", "httpcore2"):
    logging.getLogger(name).setLevel(logging.WARNING)

# Uvicorn 로그도 루트의 콘솔·파일 핸들러로 전달한다.
# 부모 로거까지 전파하고 기존 핸들러를 제거해 누락과 중복 출력을 방지한다.
for name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
    uvicorn_logger = logging.getLogger(name)
    uvicorn_logger.handlers.clear()
    uvicorn_logger.propagate = True
