# AskMate 텀 프로젝트 평가표 답변서 (QA.md)

- **프로젝트명**: AskMate (로그인 기반 범용 AI 챗봇 웹 서비스)
- **저장소**: `Codyssey-TermProject`
- **주요 기술 스택**: Python 3.14, FastAPI, SQLAlchemy 2.x, SQLite, Vanilla HTML/CSS/JS, Uvicorn, uv
- **작성일자**: 2026-09-25

---

## 1. 기본 기능 및 사용자 경험 (14개 항목)

### [x] 1. README/기술 문서에 API 명세(요청/응답 예시 포함)가 포함되어 있다
- **구현 및 근거**: 
  - [`docs/API.md`](API.md)에 모든 엔드포인트(`/api/signup`, `/api/login`, `/api/me`, `/api/logout`, `/api/chat`, `/api/me/chats`, `/health`)의 HTTP 메서드, 헤더 요구사항(`X-Requested-With`), 요청 본문, 정상 응답(200, 201, 204) 및 상태 코드별 에러 응답 예시가 완벽히 기술되어 있습니다.
  - Swagger UI(`/docs`) 및 OpenAPI 규격(`/openapi.json`)을 통해서도 실시간 확인 가능합니다.
- **참조 위치**: [`docs/API.md`](API.md), [`backend/app/main.py`](../backend/app/main.py)

### [x] 2. README/기술 문서에 DB 구조(테이블/필드 또는 ERD)가 포함되어 있다
- **구현 및 근거**:
  - [`docs/DATABASE.md`](DATABASE.md)에 `users` 및 `chats` 테이블의 세부 필드(`id`, `username`, `password_hash`, `question`, `answer`, `created_at`), 데이터 타입, PK/FK 관계 및 인덱스 설정이 명시되어 있습니다.
- **참조 위치**: [`docs/DATABASE.md`](DATABASE.md#구현된-테이블), [`backend/app/models/user.py`](../backend/app/models/user.py), [`backend/app/models/chat.py`](../backend/app/models/chat.py)

### [x] 3. README/기술 문서에 DB 확인 방법이 안내되어 있다
- **구현 및 근거**:
  - DB 기본 경로(`backend/data/askmate.db`) 안내 및 `sqlite3` CLI를 통해 데이터를 안전하게 읽기 전용으로 검증하는 절차와 전용 검증 스크립트(`scripts/check_logs.sql`) 사용법이 문서화되어 있습니다.
  - 또한 Python 단독 연결 확인 명령(`python -c "from app.db_connect import check_connection..."`) 및 본인 기록 조회 API(`GET /api/me/chats`)도 제공됩니다.
- **참조 위치**: [`docs/DATABASE.md`](DATABASE.md#로컬-db-확인용-sql), [`backend/scripts/check_logs.sql`](../backend/scripts/check_logs.sql)

### [x] 4. README/기술 문서에 팀 역할 및 개인별 작업 요약이 포함되어 있다
- **구현 및 근거**:
  - [`docs/CONVENTIONS.md`](CONVENTIONS.md)에 팀원 4인(A, B, C, D)의 역할 경계와 책임이 정의되어 있습니다.
  - 프론트엔드 작업 요약은 [`docs/FRONTEND_COMMIT_SUMMARY.md`](FRONTEND_COMMIT_SUMMARY.md) 및 [`docs/FRONTEND.md`](FRONTEND.md)에 일자별/커밋별로 상세히 정리되어 있습니다.
- **참조 위치**: [`docs/CONVENTIONS.md`](CONVENTIONS.md#2-역할과-협업-경계), [`docs/FRONTEND_COMMIT_SUMMARY.md`](FRONTEND_COMMIT_SUMMARY.md)

### [x] 5. 회원가입 기능이 동작한다
- **구현 및 근거**:
  - 아이디(3~30자, 영문/숫자/밑줄), 비밀번호(15~128자) 검증 후 Argon2id 단방향 해싱을 거쳐 DB에 저장됩니다. (중복 ID 409 Conflict 반환)
  - 웹 화면에서는 회원가입 모달(`signup-modal`)을 통해 즉시 회원가입을 수행할 수 있습니다.
- **참조 위치**: [`backend/app/account.py`](../backend/app/account.py) (`signup`), [`backend/app/security.py`](../backend/app/security.py), [`backend/app/static/js/auth_sidebar.js`](../backend/app/static/js/auth_sidebar.js)

### [x] 6. 로그인 기능이 동작한다
- **구현 및 근거**:
  - 사용자 자격증명을 검증하고, 성공 시 `askmate_session` 서명 세션 쿠키(`HttpOnly`, `SameSite=Lax`)를 발급합니다.
  - 웹 UI에서는 로그인 모달(`login-modal`)을 통해 비동기 로그인 후 즉시 사용자 상태(`setLoggedInUI`)로 전환됩니다.
- **참조 위치**: [`backend/app/account.py`](../backend/app/account.py) (`login`), [`backend/app/auth.py`](../backend/app/auth.py)

### [x] 7. 로그인/비로그인 상태에 따라 접근 가능한 기능이 구분된다
- **구현 및 근거**:
  - **백엔드**: `/api/chat`, `/api/me`, `/api/me/chats` 호출 시 `Depends(get_current_user)`를 통해 비로그인 요청에 대해 HTTP 401 Unauthorized를 엄격히 반환합니다.
  - **프론트엔드**: 비로그인 시 채팅 입력창 위에 반투명 게스트 오버레이(`guest-input-overlay`)를 노출하여 입력창 접근을 물리적으로 차단하고, 클릭 시 로그인 모달을 유도합니다.
- **참조 위치**: [`backend/app/auth.py`](../backend/app/auth.py), [`backend/app/templates/chat.html`](../backend/app/templates/chat.html), [`backend/app/static/js/auth_sidebar.js`](../backend/app/static/js/auth_sidebar.js)

### [x] 8. 웹 UI에서 질문 입력이 가능하고, 응답이 화면에 출력된다
- **구현 및 근거**:
  - 모던 2-Pane 메인 화면(`chat.html`)의 텍스트영역(`#chat-input`)에 질문을 입력하고 전송 버튼(`#send-btn`) 또는 `Enter` 키로 전송하면 사용자 말풍선 및 AI 답변 말풍선이 화면(`#chat-box`)에 순차적으로 렌더링됩니다.
- **참조 위치**: [`backend/app/templates/chat.html`](../backend/app/templates/chat.html), [`backend/app/static/js/chat.js`](../backend/app/static/js/chat.js)

### [x] 9. 질문 입력 → 서버 처리 → AI API 호출 → 응답 출력 흐름이 끊김 없이 동작한다
- **구현 및 근거**:
  - `chat.js` 전송 → `POST /api/chat` 수신 → 세션 인증 및 최근 5쌍 문맥 DB 조회 → OpenAI 호환 게이트웨이 호출(`generate_answer`) → 응답 수신 후 SQLite DB 저장 → 클라이언트로 응답 전달 → UI 로딩 표시 제거 및 답변 렌더링 파이프라인이 완전하게 연동되어 동작합니다.
- **참조 위치**: [`backend/app/llm.py`](../backend/app/llm.py), [`backend/app/llm_connect.py`](../backend/app/llm_connect.py), [`backend/app/static/js/chat.js`](../backend/app/static/js/chat.js)

### [x] 10. 사용자 질문/AI 응답이 DB에 저장된다
- **구현 및 근거**:
  - `chats` 테이블에 `user_id`, `question`, `answer`, `created_at`(UTC 시각) 필드가 매 대화마다 한 쌍으로 영구 저장됩니다. 외래키 및 트랜잭션 rollback 처리가 보장됩니다.
- **참조 위치**: [`backend/app/chat_db.py`](../backend/app/chat_db.py) (`create_chat`), [`backend/app/models/chat.py`](../backend/app/models/chat.py)

### [x] 11. 사용자 기준으로 대화 로그 조회/추적이 가능하다
- **구현 및 근거**:
  - 로그인 세션 기반의 본인 전용 조회 API `GET /api/me/chats`가 구현되어 있으며, 웹 UI 좌측 사이드바 히스토리 목록(`#history-list`)에서 본인의 과거 대화 내역이 최신순으로 자동 렌더링됩니다. 관리자/검증자는 `check_logs.sql`을 통해서도 조회 가능합니다.
- **참조 위치**: [`backend/app/history.py`](../backend/app/history.py), [`backend/app/static/js/auth_sidebar.js`](../backend/app/static/js/auth_sidebar.js) (`loadChatHistory`)

### [x] 12. AI API 실패/타임아웃 상황에서 서비스가 비정상 종료되지 않는다
- **구현 및 근거**:
  - `llm_connect.py`에서 `httpx.TimeoutException`, `httpx.HTTPStatusError`, 연결 오류 등을 감싸서 서버 다운 없이 각각 HTTP 504(타임아웃) 및 HTTP 502(외부 서비스 오류) 표준 HTTPException으로 변환합니다.
- **참조 위치**: [`backend/app/llm_connect.py`](../backend/app/llm_connect.py), [`backend/app/llm.py`](../backend/app/llm.py)

### [x] 13. 오류 발생 시 사용자에게 오류 안내(메시지/상태코드 등)가 제공된다
- **구현 및 근거**:
  - `chat.js`의 `handleChatError()`가 서버에서 전달된 HTTP 상태 코드(504, 502, 500, 401, 403, 422) 및 `detail` 에러 메시지를 파싱하여 전용 에러 말풍선(`.bubble.error-bubble`)과 얼럿으로 직관적인 사용자 안내를 제공합니다.
- **참조 위치**: [`backend/app/static/js/chat.js`](../backend/app/static/js/chat.js) (`handleChatError`)

### [x] 14. 사용자 입력 검증(빈 입력/길이 제한 등) 로직이 최소 1개 이상 존재한다
- **구현 및 근거**:
  - **프론트엔드**: 공백만 있는 입력 전송 차단, 1,000자 초과 시 입력 자동 차단 및 실시간 글자수 카운터 표시.
  - **백엔드**: Pydantic 스키마(`ChatRequest`)에서 `Field(min_length=1, max_length=1000)`로 엄격히 검증하며 공백 제거(`strip()`) 로직이 적용되어 있습니다.
- **참조 위치**: [`backend/app/llm.py`](../backend/app/llm.py#L23-L27), [`backend/app/static/js/chat.js`](../backend/app/static/js/chat.js#L14-L28)

---

## 2. 코드 품질 및 아키텍처 (8개 항목)

### [x] 1. FastAPI 프로젝트 구조가 역할 단위로 구분되어 있다
- **구현 및 근거**:
  - `models/`: DB 엔티티 정의 (`user.py`, `chat.py`)
  - 라우터 레이어: `account.py`, `llm.py`, `history.py`, `pages.py`
  - 데이터 접근 레이어(CRUD): `account_db.py`, `chat_db.py`, `db_connect.py`
  - 공통 서비스 및 보안: `auth.py`, `security.py`, `llm_connect.py`, `config.py`, `logger.py`
  - 프론트엔드: `templates/`, `static/css/`, `static/js/`로 철저히 계층화되어 있습니다.
- **참조 위치**: [`backend/app/`](../backend/app/) 하위 디렉터리 구조 및 [`README.md`](../README.md#프로젝트-구조)

### [x] 2. API 라우트가 목적에 맞게 분리되어 있다
- **구현 및 근거**:
  - 인증/계정 관련: `account.py` (`/api/signup`, `/api/login`, `/api/me`, `/api/logout`)
  - 채팅 관련: `llm.py` (`/api/chat`)
  - 대화 로그 관련: `history.py` (`/api/me/chats`)
  - 화면 뷰 관련: `pages.py` (`/`, `/login`, `/signup`, `/chat`, `/history`)
- **참조 위치**: [`backend/app/account.py`](../backend/app/account.py), [`backend/app/llm.py`](../backend/app/llm.py), [`backend/app/history.py`](../backend/app/history.py)

### [x] 3. 요청/응답 스키마를 사용하거나, 입력/출력 형식을 일관되게 관리한다
- **구현 및 근거**:
  - Pydantic BaseModel을 활용한 `SignupRequest`, `LoginRequest`, `ChatRequest`, 응답 모델 등이 각 라우터에 정의되어 입출력 데이터의 타입과 유효성을 엄격하게 관리합니다.
- **참조 위치**: [`backend/app/account.py`](../backend/app/account.py#L32-L46), [`backend/app/llm.py`](../backend/app/llm.py#L23-L27)

### [x] 4. 인증 처리 로직이 코드 상에서 분리/재사용 가능하게 구성되어 있다
- **구현 및 근거**:
  - FastAPI의 의존성 주입 시스템(`Depends`)을 활용하여 `get_current_user` 및 `require_post_header`를 `app/auth.py`에 단일 모듈로 분리하였습니다. 라우터에서는 `Depends(get_current_user)` 한 줄로 재사용합니다.
- **참조 위치**: [`backend/app/auth.py`](../backend/app/auth.py#L35-L68)

### [x] 5. DB 접근 로직이 라우터에 과도하게 섞이지 않고 분리되어 있다
- **구현 및 근거**:
  - 라우터 내부에서 직접 ORM 쿼리를 조합하지 않고, `account_db.py`(`get_user_by_username`, `create_user`) 및 `chat_db.py`(`create_chat`, `get_recent_chats_by_user`, `get_chats_by_user`)로 DB CRUD 연산을 완전히 캡슐화했습니다.
- **참조 위치**: [`backend/app/account_db.py`](../backend/app/account_db.py), [`backend/app/chat_db.py`](../backend/app/chat_db.py)

### [x] 6. 민감정보(API 키 등)가 코드에 하드코딩되어 있지 않다
- **구현 및 근거**:
  - `SESSION_SECRET_KEY`, `AI_API_KEY`, `AI_BASE_URL`, `DATABASE_PATH` 등 일체의 보안 자격 증명은 `os.environ` 기반의 `backend/app/config.py`를 통해 주입받으며, 코드 내 하드코딩된 비밀키가 존재하지 않습니다.
- **참조 위치**: [`backend/app/config.py`](../backend/app/config.py)

### [x] 7. .env 예시 제공 및 .gitignore 적용으로 민감정보가 저장소에 노출되지 않는다
- **구현 및 근거**:
  - 실제 민감정보가 포함될 수 있는 `.env`, `*.db`, 로그 파일 등은 최상위 `.gitignore`에 등록되어 Git 추적에서 원천 제외되었습니다.
  - 신규 환경 설정을 위해 안전한 키 이름과 설명이 담긴 `backend/.env.example` 템플릿이 제공됩니다.
- **참조 위치**: [`.gitignore`](../.gitignore), [`backend/.env.example`](../backend/.env.example)

### [x] 8. PR 기반 머지 기록이 존재하고, 작업 브랜치 흐름이 확인된다
- **구현 및 근거**:
  - `feature/*`, `docs/*`, `fix/*` 작업 브랜치에서 `develop`을 거쳐 배포 기준 `main`으로 병합하는 전략을 확립하였으며, Git 히스토리에 PR 머지 커밋 이력이 보존되어 있습니다.
- **참조 위치**: [`docs/CONVENTIONS.md`](CONVENTIONS.md#3-브랜치-규칙), Git Log 이력

---

## 3. 서비스 완성도 및 운영 설계 (7개 항목)

### [x] 1. REST 관점에서 API가 목적에 맞는 엔드포인트/메서드로 설계되어 있다
- **구현 및 근거**:
  - 리소스 조회는 `GET`(`/health`, `/api/me`, `/api/me/chats`), 생성/작업 수행은 `POST`(`/api/signup` [201 Created], `/api/login` [200 OK], `/api/chat` [200 OK], `/api/logout` [204 No Content])로 HTTP 표준 규격을 충실히 준수하여 설계되었습니다.
- **참조 위치**: [`docs/API.md`](API.md#공통)

### [x] 2. 인증/인가가 "왜 필요한지"가 서비스 흐름에 반영되어 있다
- **구현 및 근거**:
  - AI 챗봇 서비스 특성상 사용자별 개인화된 문맥(최근 5쌍 대화) 유지와 본인 대화 기록 보호, 악의적 게스트의 AI 토큰 남용 방지를 위해 인증이 필수적입니다. 비로그인 접근 시 백엔드 401 차단 및 프론트엔드 게스트 딤/입력 차단으로 당위성이 동작으로 직관화되어 있습니다.
- **참조 위치**: [`docs/AUTH.md`](AUTH.md), [`backend/app/auth.py`](../backend/app/auth.py)

### [x] 3. AI API 호출이 서버에서 수행되어 클라이언트에 키가 노출되지 않는다
- **구현 및 근거**:
  - 클라이언트는 오직 서버의 `/api/chat` 엔드포인트와만 통신하며, 실제 외부 LLM 게이트웨이 호출과 `AI_API_KEY` 인증 헤더 전송은 백엔드 내부의 `backend/app/llm_connect.py`에서 독점적으로 실행됩니다.
- **참조 위치**: [`backend/app/llm_connect.py`](../backend/app/llm_connect.py#L42-L68)

### [x] 4. AI 호출 실패/지연을 고려한 정책이 코드/동작으로 확인된다
- **구현 및 근거**:
  - `AI_TIMEOUT`(기본 30초) 설정 기반 타임아웃 발생 시 504 Gateway Timeout, 연결 실패 시 502 Bad Gateway로 세분화하여 예외 처리하고, 클라이언트 UI에서도 친절한 재시도 안내를 노출합니다.
- **참조 위치**: [`backend/app/llm_connect.py`](../backend/app/llm_connect.py), [`backend/app/static/js/chat.js`](../backend/app/static/js/chat.js) (`handleChatError`)

### [x] 5. 대화 로그를 왜 저장하는지(추적/운영/개선) 목적이 문서 또는 기능으로 이어진다
- **구현 및 근거**:
  - 대화 저장 목적: ① 사용자 본인의 과거 대화 이력 연속 열람(`GET /api/me/chats`), ② AI 연속 대화를 위한 직전 5쌍 문맥 주입(`get_recent_chats_by_user`), ③ 서비스 감사 및 품질 분석을 위한 관리자 검증(`scripts/check_logs.sql`)으로 이어져 실서비스 가치로 구현되었습니다.
- **참조 위치**: [`docs/DATABASE.md`](DATABASE.md#대화-저장-흐름), [`backend/app/chat_db.py`](../backend/app/chat_db.py)

### [x] 6. 로그에 "운영 추적에 필요한 사건(요청/AI/DB)"이 남아, 문제 발생 시 원인 추적이 가능하다
- **구현 및 근거**:
  - `backend/app/logger.py`를 통해 모든 중요 이벤트(`db_save_success`, `db_save_failure`, `db_read_failure`, `ai_request`, `ai_error`)를 발생 시각, 작업명, 사용자 ID, 처리 결과와 함께 구조화된 로그로 파일(`app.log`) 및 콘솔에 기록합니다. (보안을 위해 비밀번호 및 대화 본문은 로그에 남기지 않음)
- **참조 위치**: [`backend/app/logger.py`](../backend/app/logger.py), [`docs/LLM.md`](LLM.md#로깅)

### [x] 7. 협업 산출물(문서의 역할/작업 요약)이 Git 이력(커밋/PR)과 크게 모순되지 않는다
- **구현 및 근거**:
  - [`docs/CONVENTIONS.md`](CONVENTIONS.md)에 명시된 담당자 분장(A: 인증/설정, B: LLM/배포, C: 프론트엔드 UI, D: DB/로그)에 따라 커밋 단위와 PR이 분리되어 머지되었으며, [`docs/FRONTEND_COMMIT_SUMMARY.md`](FRONTEND_COMMIT_SUMMARY.md)의 커밋 해시 및 작업 내역이 실제 Git 히스토리와 정확히 일치합니다.
- **참조 위치**: [`docs/CONVENTIONS.md`](CONVENTIONS.md), [`docs/FRONTEND_COMMIT_SUMMARY.md`](FRONTEND_COMMIT_SUMMARY.md)

---

## 4. 보너스 점수 부여 (100점 가점 증빙 요약)

우리 프로젝트는 기본 요구사항을 뛰어넘어 상용 서비스 수준의 완성도와 운영 안정성을 확보하기 위해 다음의 고급 엔지니어링 요소를 추가 구현하였습니다.

1. **상용급 보안 아키텍처 구현**:
   - **Argon2id 암호화**: 최신 패스워드 해싱 표준인 Argon2id 적용 ([`backend/app/security.py`](../backend/app/security.py)).
   - **쿠키 서명 기반 세션 & CSRF 방어**: `itsdangerous` 기반 변조 방지 세션 쿠키와 모든 POST 요청에 `X-Requested-With: XMLHttpRequest` 커스텀 헤더를 강제하여 브라우저 CSRF를 원천 차단 ([`backend/app/auth.py`](../backend/app/auth.py)).
   - **XSS 방어**: 채팅 메시지 렌더링 시 `innerHTML` 대신 `textContent`를 적용하여 악의적 스크립트 실행 방지 ([`backend/app/static/js/chat.js`](../backend/app/static/js/chat.js)).
2. **지능형 다중 턴(Multi-turn) 문맥 유지**:
   - 단발성 질의응답에 그치지 않고, 사용자별 최근 5쌍의 대화를 DB에서 시간순으로 정렬·추출하여 LLM 게이트웨이에 context 메시지로 자동 주입 ([`backend/app/llm.py`](../backend/app/llm.py), [`backend/app/chat_db.py`](../backend/app/chat_db.py)).
3. **광범위한 자동화 테스트 슈트 구축**:
   - 단위/통합 테스트를 `pytest` 기반으로 구축하여 인증, DB rollback, 대화 저장, 문맥 전달, 동시성 격리 등을 자동 검증 ([`backend/tests/`](../backend/tests/)).
4. **CI/CD 및 클라우드 배포 인프라 완비**:
   - Docker 컨테이너라이징, GitHub Actions 워크플로우, Tailscale VPN을 통한 안전한 OCI(Oracle Cloud Infrastructure) 인스턴스 자동 배포 및 롤백 파이프라인 수립 ([`docs/DEPLOYMENT.md`](DEPLOYMENT.md)).
5. **최신 Python 3.14 및 uv 기반 고속 패키징**:
   - 레거시 pip 대신 차세대 패키지 매니저인 `uv`를 도입하여 환경 격리 및 완벽한 재현성(`uv.lock`)을 보장.
