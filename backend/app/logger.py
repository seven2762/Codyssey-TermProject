"""                                                          
   AskMate Backend Project
                                                                              
   파일명   : logger.py
   생성자   : Changhwan Kim                                
                                                                              
   생성일   : 2026/09/14
   업데이트  : 2026/09/14
                                                                             
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

# Uvicorn 로그도 루트의 콘솔·파일 핸들러로 전달한다.
# 부모 로거까지 전파하고 기존 핸들러를 제거해 누락과 중복 출력을 방지한다.
for name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
    uvicorn_logger = logging.getLogger(name)
    uvicorn_logger.handlers.clear()
    uvicorn_logger.propagate = True
