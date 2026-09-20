# DB·대화 기록 작업 안내 (D 담당)

## 결정된 구조

SQLite + SQLAlchemy 2.x의 동기 방식으로 구현한다. 각 개발자는 로컬 DB 파일을 사용한다.
서버 시작 시 디렉터리·DB 파일을 준비하고 연결을 확인한 뒤 없는 `users`·`chats` 테이블을 생성한다.
회원가입·로그인에 필요한 사용자 저장·조회와 대화 기록 저장이 구현되어 있다.
대화 기록 조회 API와 AI 요청에 사용할 최근 문맥 조회는 후속 작업이다.

| 파일 | 담당과 역할 |
| --- | --- |
| `backend/app/config.py` | A: 공통 환경변수와 경로 |
| `backend/app/db_connect.py` | A: engine, Base, 요청별 `get_db()` 세션 제공 |
| `backend/app/models/user.py` | A: 사용자 테이블 |
| `backend/app/account_db.py` | 사용자 저장·조회, 쓰기 시 commit·rollback |
| `backend/app/chat_db.py` | 질문·답변 저장, 쓰기 시 commit·rollback |
| `backend/app/auth.py` | 세션의 사용자 조회와 로그인 필수 검사 |
| `backend/app/security.py` | Argon2 비밀번호 해시·검증 |
| `backend/app/models/chat.py` | D: 대화 기록 테이블 |
| `backend/app/history.py` | D: 본인 기록 조회 API |
| `backend/app/templates/history.html` | D: 기록 목록 화면. C의 공통 스타일 사용 |
| `backend/data/askmate.db` | 실행 중 생성되는 로컬 데이터. Git에 올리지 않음 |

SQLite는 별도 DB 서버 설치가 필요하지 않다. `uv sync`로 SQLAlchemy 등 의존성을 설치한다.
세션·연결 객체를 라우터마다 새로 정의하지 않고 공통 `get_db`를 사용한다.

## DB 위치와 설정

`backend/.env.example`을 `backend/.env`로 복사하고 `SESSION_SECRET_KEY`를 설정한다.
기존 `.env`는 덮어쓰지 않는다. [계정·세션 인증 안내](AUTH.md) 참고.
`DATABASE_PATH=data/askmate.db`가 기본값이며, 상대 경로는 항상 `backend/` 기준이다.
쉘 또는 배포 환경에서 주입한 값이 `.env`보다 우선한다. 변경 후 서버를 재시작한다.
`DATABASE_PATH`를 생략하면 기본 DB 경로를 사용하지만, `SESSION_SECRET_KEY`는 필수이다.

`backend/`에서 연결만 확인하는 명령:

```bash
uv run python -c "from app.db_connect import check_connection; check_connection()"
```

서버 없이 사용자·대화 테이블까지 준비하려면 `check_connection` 대신 `init_db`를 호출한다.
`init_db()`는 기존 테이블과 데이터를 삭제하지 않는다.

배포에서는 `/app/data/askmate.db`와 Docker 볼륨 `askmate-data`를 사용한다.
경로 변경과 운영 DB 관련 작업은 팀장과 공유한다. [배포 안내](DEPLOYMENT.md) 참고.

## 구현된 테이블

| 테이블 | 필드 |
| --- | --- |
| `users` | `id`: 정수 PK, `username`: 중복 불가·필수 문자열, `password_hash`: 필수 문자열, `created_at`: UTC 생성 시각 |
| `chats` | `id`: 정수 PK, `user_id`: 필수 정수 FK → users.id, `question`: 필수 Text, `answer`: 필수 Text, `created_at`: UTC 생성 시각 |

`users`는 구현되어 있으며 `username`의 UNIQUE 제약으로 동시 가입 시에도 중복을 막는다.
`password_hash`에는 salt와 파라미터가 포함된 Argon2 해시 문자열을 저장한다.
별도의 공통 salt나 pepper 환경변수는 사용하지 않는다.
`created_at`은 SQLite에 시간대 정보 없이 UTC로 저장한다. 이후 API에서 반환할 때는
UTC로 해석하여 `Z` 또는 `+00:00`이 포함된 ISO 8601 문자열로 변환한다.

`chats.user_id`에는 조회용 인덱스가 있다. SQLite 외래 키 검사는 연결마다 활성화한다.
테이블 생성 시 모든 모델이 먼저 import되어야 한다. `Base.metadata.create_all()`은
기존 테이블의 구조를 변경해주지 않으므로 필드 변경은 A와 함께 초기화·마이그레이션 방법을 정한다.

## 대화 저장 흐름

`POST /api/chat → 로그인·입력 확인 → AI 답변 수신 → create_chat() → 성공 응답` 순서이다.
`chat_db.create_chat(db, user_id, question, answer)`는 질문·답변 한 쌍을 저장하고 기록 ID를 반환한다.
사용자 ID는 로그인 세션에서 확인한 `user.id`를 사용하며 요청 본문의 ID는 사용하지 않는다.
질문은 앞뒤 공백을 제거한 값, 답변은 AI 통신 함수에서 반환한 문자열을 저장한다.

- `llm.py`에서 답변을 받은 뒤 저장 함수를 스레드에서 실행한다. AI 대기 중에는 쓰기 작업을 시작하지 않는다.
- 저장이 완료되면 `{"answer":"..."}`를 반환하고 `db_save_success operation=chat`을 기록한다.
- 저장에 실패하면 rollback하고 `db_save_failure operation=chat`과 HTTP 500을 반환한다.
  오류 응답은 `{"detail":"대화 기록을 저장하지 못했습니다."}`이며 성공한 대화로 저장하지 않는다.
- AI 답변을 받지 못한 요청과 인증·입력 검증을 통과하지 못한 요청은 저장하지 않는다.
- 질문·답변 본문은 DB에만 저장하고 서버 로그에는 사용자 ID와 기록 ID 등 처리 결과를 남긴다.

실제 AI 통신은 아직 구현되지 않아 일반 실행에서는 501을 반환한다.
`tests/test_chat_storage.py`는 통신 함수를 테스트용 응답으로 대체해 API와 DB 저장을 검증한다.
저장 확인만을 위한 공개 API는 추가하지 않는다. 환경 변수와 의존성 변경도 없다.

## 이후 구현할 조회 기능

1. `history.py`에 `GET /me/chats`를 구현한다. `main.py`가 `/api`를 붙인다.
2. `history.html`에서 `/api/me/chats`를 호출해 최신순 목록과 빈 목록 안내를 표시한다.
3. `backend/scripts/check_logs.sql`에 사용자 기준 확인용 쿼리를 추가하고 실행 방법을 문서화한다.

API는 `Depends(get_current_user)`와 `Depends(get_db)`를 사용한다.
`get_current_user`는 `app.auth`에서 가져오며 반환된 `User`의 `id`를 조회 조건에 사용한다.
클라이언트가 보낸 사용자 ID를 신뢰하지 않고 서버에서 확인한 사용자로 필터링한다.
로그인 세션은 서명 쿠키로 처리하므로 추가 세션 테이블이나 users 필드 변경은 없다.

예정된 조회 API의 성공 응답 규격은 다음과 같다. 기록이 없으면 `[]`를 반환한다.

```json
[{"id":1,"question":"질문","answer":"답변","created_at":"2026-09-15T00:00:00Z"}]
```

정렬은 `created_at DESC, id DESC`, 시간은 UTC ISO 8601 문자열로 반환한다.
세션은 요청별로 쓰고 종료한다. 쓰기 작업은 명시적으로 commit하고 실패하면 rollback한다.
AI 호출을 기다리는 동안 쓰기 트랜잭션을 유지하지 않는다.
질문·답변 저장은 `llm.py`에 연결되어 있으므로 AI 연동 시 기존 저장 처리를 유지한다.

## 작업 완료 확인

- 서로 다른 두 사용자의 기록이 섞이지 않는다.
- 서버 재시작 후 기록이 유지되고, 빈 목록과 최신순 조회가 정상이다.
- 저장 실패 로그와 rollback을 확인한다.
- 실행 검증은 임시 DB로 수행하고 다른 팀원의 데이터나 운영 DB를 초기화하지 않는다.
- `feature/chat-history`에서 작업하고 `develop` 대상으로 PR을 작성한다.

## 자동 검증

`backend/`에서 실행한다. `uv sync`는 개발용 테스트 도구도 함께 설치한다.

```bash
uv sync --locked
uv run python -m pytest -q
```

테스트는 임시 DB와 임시 로그 디렉터리를 사용한다. 정상 가입, 입력 검증, 중복·동시 가입,
해시 저장, DB 오류 시 rollback, 로그인·로그아웃·쿠키와 접근 제어, 재시작 후 데이터 유지를 확인한다.
대화 저장 테스트는 사용자 연결·UTC 시각·누적 저장, 외래 키와 commit 실패 시 rollback,
실패 응답·로그, 기존 사용자 DB에 테이블 추가 및 별도 프로세스 재시작 후 기록 유지를 확인한다.

저장 기능만 검증하려면 `uv run python -m pytest tests/test_chat_storage.py -q`를 실행한다.

현재 Starlette 1.6.0의 TestClient 내부에서 AnyIO `BlockingPortal` 별칭의 폐기 예정 경고가
발생한다. 테스트용 HTTP 도구는 공식 권장인 `httpx2`를 사용하며, 이 경고를 숨기지는 않는다.
