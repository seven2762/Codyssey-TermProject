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
| `backend/app/pages.py` | 화면 경로와 로그인 상태에 따른 이동 |

`history.html`의 기록 목록 구현은 D 담당이다. C는 공통 레이아웃과 스타일을 제공한다.
각 HTML은 `base.html`을 상속하고 `title`, `content` 블록을 채운다.

## 먼저 실행하기

저장소 루트에서 다음 명령을 실행한다.

```bash
cd backend
uv sync
# 최초 실행: .env.example을 .env로 복사하고 SESSION_SECRET_KEY 설정 (아래 인증 안내 참고)
uv run uvicorn app.main:app --reload
```

브라우저에서 `http://127.0.0.1:8000/login`에 접속한다.
화면은 현재 안내 문구가 있는 골격이다. `/chat`, `/history`는 로그인 후에만 접근할 수 있다.
HTML 파일을 직접 열지 않고 FastAPI 주소로 접속한다.
[계정·세션 인증 안내](AUTH.md)의 `.env` 설정을 먼저 완료한다.

## 구현 순서와 API 약속

전체 요청·응답 규격은 [API 명세](API.md)를 참고한다.
`static/js/main.js`의 `signupUser(username, password)`는 실제 회원가입 API를 호출하는 예시이다.
폼의 submit 처리에서 호출하면 성공 시 `{id, username}`을 반환하고, 실패 시 `Error`를 던진다.
입력 검증 오류와 중복 가입 안내는 `catch`에서 `error.message`로 표시한다.

1. 로그인·회원가입 폼과 채팅 화면을 작성한다.
2. 채팅에 공백 입력 차단, 1,000자 제한, 전송 중 버튼 비활성화와 오류 표시를 넣는다.
3. 아래 API가 담당자의 PR에서 완성되면 JavaScript의 `fetch`로 연결한다.

화면 경로는 `/login`처럼 사용하고, 데이터 요청은 `/api/*`로 보낸다.
요청 본문은 JSON이며 `Content-Type: application/json`을 지정한다.
모든 POST 요청에 `X-Requested-With: XMLHttpRequest` 헤더를 추가한다. 누락·다른 값은 403이다.
다음 표는 후속 구현의 공통 규격이며 현재 전부 구현된 API 목록이 아니다.

| API | 요청 | 성공 응답 | 현재 상태 |
| --- | --- | --- | --- |
| `POST /api/signup` | `{"username":"...","password":"..."}` | 201, `{"id":1,"username":"..."}` | 구현 완료, SQLite에 사용자 저장 |
| `POST /api/login` | `{"username":"...","password":"..."}` | 200, `{"id":1,"username":"..."}` + 세션 쿠키 | 구현 완료 |
| `GET /api/me` | 본문 없음 | 200, `{"id":1,"username":"..."}` | 구현 완료, 비로그인은 401 |
| `POST /api/logout` | 본문 없음 | 204, 본문 없음 | 구현 완료 |
| `POST /api/chat` | `{"question":"..."}` | 200, `{"answer":"..."}` | 구현 완료, 로그인 필요. 실패 코드는 아래 참고 |
| `GET /api/me/chats` | 본문 없음 | 200, 기록 배열. [DB 안내](DATABASE.md) 참고 | 구현 완료, 본인 기록만 최신순 반환 |

채팅 API는 AI 답변을 받은 뒤 DB 저장까지 성공해야 200을 반환한다.
실패는 상태 코드로 구분해 안내한다. `detail`은 그대로 표시해도 되는 문구이며,
제공자 오류 상세나 키는 들어 있지 않다.

| 상태 | 상황 | 화면 안내 |
| --- | --- | --- |
| 504 | AI 응답 지연 | 다시 시도 버튼을 함께 보여준다 |
| 502 | AI 연결 실패 | 다시 시도 버튼을 함께 보여준다 |
| 500 | 문맥 조회·대화 저장 실패 | `detail` 문구를 그대로 표시한다 |
| 422 | 빈 입력·1,000자 초과 | 입력창 옆에 표시한다 |
| 401 | 비로그인·세션 만료 | 로그인 화면으로 이동한다 |
| 403 | `X-Requested-With` 헤더 누락 | 요청 코드의 버그이므로 수정한다 |

실패한 질문은 저장되지 않으므로 기록 화면에도 나타나지 않는다.
응답까지 1초 내외가 걸리므로 전송 버튼을 비활성화하고 로딩 표시를 보여준다.

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
  -H 'X-Requested-With: XMLHttpRequest' \
  -d '{"username":"demo_user","password":"example password phrase"}'
```

인증은 서명된 HttpOnly 세션 쿠키로 구현되어 있다. 토큰을 localStorage에 저장하지 않는다.
같은 서버의 상대 URL로 요청하고, 사용자 ID를 요청에 넣어 인증을 대신하지 않는다.
`/chat`·`/history` 화면과 채팅·기록 API에는 로그인 제한이 적용되어 있다.
로그인은 아래처럼 호출한다. `username`, `password`는 폼에서 읽은 값이다.

```javascript
const response = await fetch("/api/login", {
    method: "POST",
    headers: {
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
    },
    body: JSON.stringify({ username, password }),
});
const data = await response.json();
if (response.ok) {
    window.location.assign("/chat");
} else {
    // data.detail로 폼의 오류 메시지를 표시한다. 422이면 배열이다.
}
```

같은 출처의 fetch에는 브라우저가 쿠키를 자동으로 전송한다. JavaScript에서 쿠키를 읽을 필요가 없다.
로그인 비밀번호는 1~128자를 받으며, 가입 화면의 15자 최소 조건을 로그인 화면에 적용하지 않는다.
잘못된 사용자명과 비밀번호는 모두 401과 같은 안내를 반환한다.
`GET /api/me`는 현재 사용자 표시용이다. 보호된 API의 401은 로그인 화면으로 안내한다.
로그아웃은 공통 헤더와 함께 `POST /api/logout`을 보내고, 성공하면 `/login`으로 이동한다.
204에서는 JSON을 파싱하지 않는다. 화면 폼·버튼의 실제 연결은 프론트 작업으로 진행한다.

에러는 `response.ok`로 먼저 구분한다. 기본 오류 본문은 `{"detail": ...}`이며,
입력 검증 오류(422)의 `detail`은 배열일 수 있다. 사용자에게 읽을 수 있는 안내를 표시한다.
204 응답에는 JSON 파싱을 시도하지 않는다.
AI 답변과 사용자 입력을 DOM에 추가할 때는 `textContent`를 사용한다.
Jinja2에서 사용자 입력에 `|safe`를 적용하지 않는다.

## 내 대화 기록 연결

`history.html`의 기록 목록에서 `GET /api/me/chats`를 호출한다.
사용자 ID나 요청 본문, POST용 헤더는 필요하지 않으며 같은 출처의 세션 쿠키로 본인을 확인한다.

```javascript
const response = await fetch("/api/me/chats");
const data = await response.json();
if (response.status === 401) {
    window.location.assign("/login");
} else if (!response.ok) {
    // data.detail을 오류 메시지로 표시한다. 빈 기록으로 처리하지 않는다.
} else {
    // data는 최신순 배열이다. []이면 "대화 기록이 없습니다."를 표시한다.
    // 각 항목의 question, answer는 textContent로 출력한다.
    // 생성 시각은 new Date(item.created_at).toLocaleString()으로 표시할 수 있다.
}
```

항목은 `id`, `question`, `answer`, `created_at`을 포함한다.
시간은 `2026-09-20T03:00:00Z`처럼 UTC로 전달하며 브라우저에서 사용자 시간대로 표시한다.
API는 현재 본인의 전체 기록을 `created_at DESC, id DESC` 순서로 반환한다.
조회 실패는 500과 `{"detail":"대화 기록을 불러오지 못했습니다."}`로 안내한다.
응답에는 `Cache-Control: no-store`가 적용되어 있다. 화면의 목록 표시는 프론트에서 구현한다.

## 작업 완료 확인

- 작은 화면에서도 입력·전송·오류 메시지를 확인할 수 있다.
- 빈 입력과 긴 입력을 차단하고, 실패 후 다시 전송할 수 있다.
- AI 실패(504·502)를 성공이나 가짜 AI 답변으로 표시하지 않는다.
- `feature/frontend`에서 작업하고 `develop` 대상으로 PR을 작성한다.
- API 경로나 공통 `main.py`를 변경할 때는 A·B·D와 공유한다.
