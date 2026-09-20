# 계정·세션 인증

회원가입, 로그인, 현재 사용자 확인, 로그아웃과 채팅·기록 화면 접근 제어를 구현했다.
화면 폼과 버튼은 프론트에서 연결한다. 답변 수신 후 대화 저장은 연결되어 있으며,
실제 AI 호출과 문맥 구성·대화 기록 조회는 후속 작업이다.

## 실행 설정

`backend/`에서 실행한다. `.env`가 이미 있다면 덮어쓰지 말고 필요한 설정만 추가한다.

```bash
uv sync
cp .env.example .env  # .env가 없을 때만 실행
uv run python -c "import secrets; print(secrets.token_urlsafe(32))"
```

마지막 명령의 결과를 `.env`의 `SESSION_SECRET_KEY`에 넣은 뒤
`uv run uvicorn app.main:app --reload`로 실행한다. 실제 키는 공유하거나 Git에 올리지 않는다.

| 설정 | 기본값 | 의미 |
| --- | --- | --- |
| `SESSION_SECRET_KEY` | 없음, 필수 | 세션 쿠키 서명용 무작위 비밀키 |
| `SESSION_MAX_AGE` | `3600` | 로그인 후 유효기간(초), 양의 정수 |
| `SESSION_HTTPS_ONLY` | `false` | `true`이면 HTTPS에서만 쿠키 전송 |
| `DATABASE_PATH` | `data/askmate.db` | 기존 사용자 SQLite DB 경로 |

실행 환경에서 전달한 값이 `.env`보다 우선한다. 비밀키가 없거나 비어 있으면 시작하지 않는다.
키는 실행할 때마다 바꾸지 않는다. DB와 키가 같으면 유효기간 내 로그인은 서버 재시작 후에도 유지된다.
키를 교체하면 기존 세션은 모두 무효가 된다. 여러 프로세스는 같은 키를 사용해야 한다.
HTTPS 배포 시 `SESSION_HTTPS_ONLY=true`를 설정한다. 로컬 HTTP에서 true로 설정하면
로그인 응답을 받아도 이후 HTTP 요청에는 쿠키가 전송되지 않는다.

## API 규격

화면과 API는 같은 출처(프로토콜·호스트·포트)에서 제공한다.
모든 POST 요청에는 `X-Requested-With: XMLHttpRequest` 헤더가 필요하다.
본문이 있는 요청은 JSON과 `Content-Type: application/json`을 사용한다.

| API | 요청 | 성공 |
| --- | --- | --- |
| `POST /api/signup` | `username`, `password` | 201, `{"id":1,"username":"demo_user"}` |
| `POST /api/login` | `username`, `password` | 200, 같은 사용자 정보와 세션 쿠키 |
| `GET /api/me` | 본문 없음 | 200, 현재 사용자 정보 |
| `POST /api/logout` | 본문 없음 | 204, 본문 없음·현재 브라우저의 쿠키 삭제 |

사용자명은 앞뒤 공백 제거·소문자 변환 후 영문·숫자·밑줄 3~30자로 검사한다.
가입 비밀번호는 15~128자, 로그인 비밀번호는 1~128자를 받는다. 로그인은 가입 정책 대신
저장된 해시와의 일치 여부를 확인하므로 최소 길이를 분리한다. 비밀번호를 trim하거나 변환하지 않는다.
가입 성공은 자동 로그인이 아니며, 로그인 성공 뒤 프론트가 `/chat`으로 이동한다.

- 잘못된 사용자명 또는 비밀번호: 401, `사용자명 또는 비밀번호가 올바르지 않습니다.`
- 로그인하지 않았거나 세션이 만료·변조됨: 보호된 API는 401, `로그인이 필요합니다.`
- 공통 POST 헤더가 없거나 값이 다름: 403. 이 검사가 인증·본문 검증보다 먼저 수행된다.
- 입력 형식 오류: 422. `detail` 배열에 필드 위치와 오류 메시지를 반환하며 원본 입력은 제외한다.
- 사용자 조회 장애: 500, `로그인 정보를 확인하지 못했습니다.`. 내부 DB 오류는 서버 로그에만 남긴다.
- 로그아웃은 이미 비로그인 상태여도 204를 반환한다. 실패한 로그인 요청은 기존 세션을 바꾸지 않는다.

`/chat`, `/history` 화면은 비로그인이면 303으로 `/login`에 이동시킨다.
로그인한 사용자가 `/login`을 열면 303으로 `/chat`에 이동시킨다.
`/signup`, `/health`, `/docs`, 정적 파일은 공개한다.

## 코드 연결

`account.py`는 요청·응답 모델과 API, `account_db.py`는 SQLAlchemy 조회·저장,
`security.py`는 Argon2 해시·검증을 담당한다. `main.py`는 SessionMiddleware를 등록한다.

`auth.py`의 `get_session_user`는 세션의 ID로 DB를 조회하고 사용자 또는 None을 반환한다.
`get_current_user`는 여기에 로그인 필수 검사를 추가한다. 이후 기록 API에서도 다음 형태로 사용한다.

```python
from typing import Annotated
from fastapi import Depends
from app.auth import get_current_user
from app.models.user import User

# 라우터 함수의 인자: user: Annotated[User, Depends(get_current_user)]
# 기록 조회·저장에는 클라이언트가 보낸 ID 대신 user.id를 사용한다.
```

상태를 변경하는 API에는 `dependencies=[Depends(require_csrf_header)]`를 연결한다.
`llm.py`에는 두 검사가 이미 연결되어 있다. 로그인 전에는 AI 함수를 호출하지 않는다.

## 쿠키 정책과 범위

`askmate_session`은 `user_id`만 담는 서명된 쿠키이다. `HttpOnly`, `SameSite=Lax`,
`Path=/`를 사용하며, 비밀번호·해시를 넣지 않는다. 서명은 암호화가 아니므로 내용은 읽을 수 있다.
현재 잠금 버전인 Starlette 1.6.0에서는 세션을 수정할 때만 쿠키를 다시 발급한다.
사용자 조회·페이지 접속만으로 유효기간이 연장되지 않는다.

세션 테이블이나 메모리 저장소는 없다. 로그아웃은 현재 브라우저의 쿠키를 삭제하며,
다른 브라우저의 로그인이나 이미 복사된 쿠키를 서버에서 즉시 폐기하지 않는다.
복사된 쿠키도 서명이 유효하면 만료 전까지 사용 가능하다. 개별 세션을 즉시 폐기하는 기능이
필요해지면 서버 저장 방식으로 변경한다. 삭제된 사용자 계정은 DB 조회에서 걸러진다.

CSRF 방지는 공통 커스텀 헤더 검사와 다른 출처에 CORS를 허용하지 않는 설정을 함께 사용한다.
프론트를 별도 출처로 옮길 때에는 이 전제를 다시 검토한다.
로그에는 요청 수신, 로그인 성공·실패, 로그아웃과 DB 조회 오류를 남기며
비밀번호·해시·쿠키·서명키·전체 요청 헤더를 기록하지 않는다.

## 검증

`backend/`에서 `uv run python -m pytest -q`로 실행한다. 테스트는 임시 DB·로그·테스트용 키를 사용한다.
회원가입 회귀, 로그인 입력, 사용자별 쿠키 분리, 만료·변조, 로그아웃, 접근 제한,
CSRF 헤더, DB 장애, 재시작과 환경변수·HTTPS 쿠키 동작을 확인한다.
실제 외부 AI 호출과 OCI 배포 검증은 포함하지 않는다.

기술 근거: [Starlette 세션](https://starlette.dev/middleware/#sessionmiddleware),
[pwdlib 검증](https://frankie567.github.io/pwdlib/reference/pwdlib/#pwdlib.PasswordHash.verify),
[OWASP API용 커스텀 헤더](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html#employing-custom-request-headers-for-ajaxapi).
