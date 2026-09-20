# 프론트 작업 안내 (C 담당)

## 결정된 구조

Jinja2 + HTML/CSS/기본 JavaScript를 사용한다. FastAPI가 화면과 API를 함께 제공한다.
별도 프론트 서버나 빌드 도구는 필요하지 않다.

| 파일 | 작업 내용 |
| --- | --- |
| `backend/app/templates/base.html` | 공통 HTML, 메뉴, CSS·JS 연결 |
| `backend/app/templates/login.html` | 로그인 폼 |
| `backend/app/templates/signup.html` | 회원가입 폼 |
| `backend/app/templates/chat.html` | 질문 입력·답변·로딩·오류 표시 |
| `backend/app/static/css/style.css` | 공통 스타일 |
| `backend/app/static/js/main.js` | 화면 이벤트·API 호출. 기능이 늘면 화면별 JS로 분리 가능 |
| `backend/app/static/images/` | 이미지 |
| `backend/app/pages.py` | 화면을 반환하는 경로. 인증 연결은 A 담당 |

`history.html`의 기록 목록 구현은 D 담당이다. C는 공통 레이아웃과 스타일을 제공한다.
각 HTML은 `base.html`을 상속하고 `title`, `content` 블록을 채운다.

## 먼저 실행하기

저장소 루트에서 다음 명령을 실행한다.

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload
```

브라우저에서 `http://127.0.0.1:8000/login`에 접속한다.
`/signup`, `/chat`, `/history`도 현재는 안내 문구가 있는 빈 화면이다.
HTML 파일을 직접 열지 않고 FastAPI 주소로 접속한다.

## 구현 순서와 API 약속

1. 로그인·회원가입 폼과 채팅 화면을 작성한다.
2. 채팅에 공백 입력 차단, 1,000자 제한, 전송 중 버튼 비활성화와 오류 표시를 넣는다.
3. 아래 API가 담당자의 PR에서 완성되면 JavaScript의 `fetch`로 연결한다.

화면 경로는 `/login`처럼 사용하고, 데이터 요청은 `/api/*`로 보낸다.
요청 본문은 JSON이며 `Content-Type: application/json`을 지정한다.
다음 표는 후속 구현의 공통 규격이며 현재 전부 구현된 API 목록이 아니다.

| API | 요청 | 성공 응답 | 현재 상태 |
| --- | --- | --- | --- |
| `POST /api/signup` | `{"username":"...","password":"..."}` | 201, `{"id":1,"username":"..."}` | 구현 완료, SQLite에 사용자 저장 |
| `POST /api/login` | `{"username":"...","password":"..."}` | 200, `{"id":1,"username":"..."}` + 세션 쿠키 | A 구현 예정, 현재 404 |
| `POST /api/logout` | 본문 없음 | 204, 본문 없음 | A 구현 예정, 현재 404 |
| `POST /api/chat` | `{"question":"..."}` | 200, `{"answer":"..."}` | 연결 골격만 있음, 정상 입력도 현재 501 |
| `GET /api/me/chats` | 본문 없음 | 200, 기록 배열. [DB 안내](DATABASE.md) 참고 | D 구현 예정, 현재 404 |

비밀번호 확인은 가입 화면에서 입력값을 비교하며 요청에는 `username`, `password`만 보낸다.
회원가입 입력 규칙과 응답은 아래와 같다.

- 사용자명: 앞뒤 공백을 제거한 뒤 3~30자, 영문·숫자·밑줄(`_`)만 허용한다.
  소문자로 저장하므로 `Charles`와 `charles`는 같은 사용자명이다.
- 비밀번호: 15~128자이며 공백과 유니코드 문자를 허용한다. `trim()`이나 소문자 변환을 하지 않는다.
- 성공: 201과 `id`, `username`을 반환한다. 자동 로그인하지 않으며, 프론트에서 로그인 화면으로 이동시킨다.
- 중복: 409, `{"detail":"이미 사용 중인 사용자명입니다."}`.
- 입력 오류: 422, `detail` 배열의 `loc`, `msg`, `type`으로 필드별 안내를 표시한다.
  서버는 원본 입력을 응답에 포함하지 않는다.
- 저장 실패: 500, `{"detail":"회원가입 정보를 저장하지 못했습니다."}`.

서버 실행 후 API만 확인하는 예시 (테스트용 계정이 DB에 생성됨):

```bash
curl -i http://127.0.0.1:8000/api/signup \
  -H 'Content-Type: application/json' \
  -d '{"username":"demo_user","password":"example password phrase"}'
```

인증은 A가 서명된 HttpOnly 세션 쿠키로 구현한다. 토큰을 localStorage에 저장하는 구조를 만들지 않는다.
같은 서버의 상대 URL로 요청하고, 사용자 ID를 요청에 넣어 인증을 대신하지 않는다.
인증 도입 후 `/chat`·`/history` 화면과 채팅·기록 API에는 로그인 제한을 적용한다.
현재 화면은 인증 연결 전의 골격이므로 화면 접근이 된다고 로그인에 성공한 것은 아니다.

에러는 `response.ok`로 먼저 구분한다. 기본 오류 본문은 `{"detail": ...}`이며,
입력 검증 오류(422)의 `detail`은 배열일 수 있다. 사용자에게 읽을 수 있는 안내를 표시한다.
204 응답에는 JSON 파싱을 시도하지 않는다.
AI 답변과 사용자 입력을 DOM에 추가할 때는 `textContent`를 사용한다.
Jinja2에서 사용자 입력에 `|safe`를 적용하지 않는다.

## 작업 완료 확인

- 작은 화면에서도 입력·전송·오류 메시지를 확인할 수 있다.
- 빈 입력과 긴 입력을 차단하고, 실패 후 다시 전송할 수 있다.
- 아직 없는 API의 404/501을 성공이나 가짜 AI 답변으로 표시하지 않는다.
- `feature/frontend`에서 작업하고 `develop` 대상으로 PR을 작성한다.
- API 경로나 공통 `main.py`를 변경할 때는 A·B·D와 공유한다.
