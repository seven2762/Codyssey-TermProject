# DB·대화 기록 작업 안내 (D 담당)

## 결정된 구조

SQLite + SQLAlchemy 2.x의 동기 방식으로 구현한다. 각 개발자는 로컬 DB 파일을 사용한다.
현재는 서버 시작 시 디렉터리·DB 파일을 준비하고 `SELECT 1`로 연결만 확인한다.
사용자·대화 테이블과 저장·조회 기능은 아직 없다.

| 파일 | 담당과 역할 |
| --- | --- |
| `backend/app/config.py` | A: 공통 환경변수와 경로 |
| `backend/app/db_connect.py` | A: engine, Base, 요청별 `get_db()` 세션 제공 |
| `backend/app/models/user.py` | A: 사용자 테이블 |
| `backend/app/models/chat.py` | D: 대화 기록 테이블 |
| `backend/app/history.py` | D: 본인 기록 조회 API |
| `backend/app/templates/history.html` | D: 기록 목록 화면. C의 공통 스타일 사용 |
| `backend/data/askmate.db` | 실행 중 생성되는 로컬 데이터. Git에 올리지 않음 |

SQLite는 별도 DB 서버 설치가 필요하지 않다. `uv sync`로 SQLAlchemy 등 의존성을 설치한다.
세션·연결 객체를 라우터마다 새로 정의하지 않고 공통 `get_db`를 사용한다.

## DB 위치와 설정

선택적으로 `backend/.env.example`을 `backend/.env`로 복사한다.
`DATABASE_PATH=data/askmate.db`가 기본값이며, 상대 경로는 항상 `backend/` 기준이다.
쉘 또는 배포 환경에서 주입한 값이 `.env`보다 우선한다. 변경 후 서버를 재시작한다.
환경변수 없이도 기본 경로로 실행된다.

`backend/`에서 연결만 확인하는 명령:

```bash
uv run python -c "from app.db_connect import check_connection; check_connection()"
```

배포에서는 `/app/data/askmate.db`와 Docker 볼륨 `askmate-data`를 사용한다.
경로 변경과 운영 DB 관련 작업은 팀장과 공유한다. [배포 안내](DEPLOYMENT.md) 참고.

## 테이블 규격과 구현 순서

1. `from app.db_connect import Base`를 사용해 아래 모델을 정의한다.
2. A의 사용자 모델과 외래 키를 연결하고 테이블 생성 진입점을 A와 함께 추가한다.
3. `history.py`에 `GET /me/chats`를 구현한다. `main.py`가 `/api`를 붙인다.
4. `history.html`에서 `/api/me/chats`를 호출해 최신순 목록과 빈 목록 안내를 표시한다.
5. `backend/scripts/check_logs.sql`에 사용자 기준 확인용 쿼리를 추가하고 실행 방법을 문서화한다.

| 테이블 | 필드 |
| --- | --- |
| `users` | `id`: 정수 PK, `username`: 중복 불가·필수 문자열, `password_hash`: 필수 문자열, `created_at`: UTC 생성 시각 |
| `chats` | `id`: 정수 PK, `user_id`: 필수 정수 FK → users.id, `question`: 필수 Text, `answer`: 필수 Text, `created_at`: UTC 생성 시각 |

`chats.user_id`에는 조회용 인덱스를 둔다. SQLite 외래 키 검사는 연결마다 이미 활성화한다.
테이블 생성 시 모든 모델이 먼저 import되어야 한다. `Base.metadata.create_all()`은
기존 테이블의 구조를 변경해주지 않으므로 필드 변경은 A와 함께 초기화·마이그레이션 방법을 정한다.

API는 A가 제공할 현재 로그인 사용자와 `Depends(get_db)`를 사용한다.
클라이언트가 보낸 사용자 ID를 신뢰하지 않고 서버에서 확인한 사용자로 필터링한다.
현재 인증 기능은 미구현이므로 전체 사용자 기록을 공개하는 임시 API는 만들지 않는다.

성공 응답 규격은 다음과 같다. 기록이 없으면 `[]`를 반환한다.

```json
[{"id":1,"question":"질문","answer":"답변","created_at":"2026-09-15T00:00:00Z"}]
```

정렬은 `created_at DESC, id DESC`, 시간은 UTC ISO 8601 문자열로 반환한다.
세션은 요청별로 쓰고 종료한다. 쓰기 작업은 명시적으로 commit하고 실패하면 rollback한다.
AI 호출을 기다리는 동안 쓰기 트랜잭션을 유지하지 않는다.
질문·답변 저장 호출은 B의 `llm.py`에서 연결하므로 모델과 저장 방법을 B에게 공유한다.

## 작업 완료 확인

- 서로 다른 두 사용자의 기록이 섞이지 않는다.
- 서버 재시작 후 기록이 유지되고, 빈 목록과 최신순 조회가 정상이다.
- 저장 실패 로그와 rollback을 확인한다.
- 실행 검증은 임시 DB로 수행하고 다른 팀원의 데이터나 운영 DB를 초기화하지 않는다.
- `feature/chat-history`에서 작업하고 `develop` 대상으로 PR을 작성한다.
