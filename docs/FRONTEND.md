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

----------------------------------
Revied by seven2762 2026/09/23
commented
3 days ago
Owner
리뷰 — 실제로 합쳐서 실행해 봤습니다
feature/frontend를 최신 develop에 로컬 머지하고 서버를 띄워 확인했습니다.
UI 구조와 CSS, textContent 기반 XSS 방지, 커밋 7개 분리는 좋았습니다.
다만 현재 상태로 머지하면 화면이 동작하지 않습니다. 원인과 해결 방법을 정리합니다.

먼저: 근본 원인은 브랜치 분기 시점입니다
이 브랜치는 f339d74(PR #7 머지)에서 갈라졌습니다. A의 인증 작업 PR #8~#16 이전 시점입니다.
그 사이 develop에 세션 인증과 CSRF 헤더 검사가 들어왔는데, 이 브랜치는 그걸 모르는 상태입니다.

텍스트 충돌이 없어서 GitHub이 CLEAN으로 표시하지만, 실제로는 API 규격이 달라졌습니다.
아래 1~3번이 전부 여기서 나옵니다. 코드 자체의 문제라기보다 기준 브랜치 문제입니다.

최신 develop을 먼저 머지하거나 리베이스해 주세요.

🔴 1. POST 요청 4개가 모두 403입니다
재현
curl -s -o /dev/null -w '%{http_code}\n' -X POST http://127.0.0.1:8000/api/signup \
  -H 'Content-Type: application/json' \
  -d '{"username":"testuser","password":"correct-horse-battery"}'
# 403
실제 결과:

POST /api/signup  -> 403 {"detail":"X-Requested-With: XMLHttpRequest 헤더가 필요합니다."}
POST /api/login   -> 403 (동일)
POST /api/logout  -> 403 (동일)
POST /api/chat    -> 403 (동일)
회원가입·로그인·로그아웃·채팅이 전부 막힙니다.

원인
A가 PR #10에서 CSRF 방어를 추가했습니다. backend/app/auth.py:15-23

def require_csrf_header(requested_with = Header(alias="X-Requested-With")) -> None:
    """브라우저의 다른 출처에서 전송한 단순 요청을 차단한다."""
    if requested_with != "XMLHttpRequest":
        raise HTTPException(status_code=403, detail="X-Requested-With: XMLHttpRequest 헤더가 필요합니다.")
POST 엔드포인트 전부에 의존성으로 걸려 있습니다.
account.py:61(signup), :83(login), :115(logout), llm.py:43(chat)

공격자 사이트의 <form method="post">는 사용자의 세션 쿠키를 실어 보낼 수 있지만
커스텀 헤더는 붙일 수 없습니다. 커스텀 헤더가 붙으면 브라우저가 CORS preflight를 먼저 보내고,
서버가 허용하지 않으면 본 요청이 막힙니다. 그래서 이 헤더의 존재가 "같은 출처의 JS 요청"이라는 증거가 됩니다.

GET 요청(/api/me, /api/me/chats)에는 걸려 있지 않아 그대로 두시면 됩니다.

해결
static/js/chat.js:52

-            headers: { 'Content-Type': 'application/json' },
+            headers: {
+                'Content-Type': 'application/json',
+                'X-Requested-With': 'XMLHttpRequest',
+            },
static/js/auth_sidebar.js:216(login), :268(signup) — 위와 동일합니다.

static/js/auth_sidebar.js:300(logout) — 헤더 객체 자체가 없습니다.

-        const response = await fetch('/api/logout', { method: 'POST' });
+        const response = await fetch('/api/logout', {
+            method: 'POST',
+            headers: { 'X-Requested-With': 'XMLHttpRequest' },
+        });
네 군데에 흩어두면 다음에 POST가 늘 때 또 빠질 수 있어서, 공용 헬퍼를 권합니다.

async function postJSON(url, body) {
    return fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',  // 서버 CSRF 검사. docs/AUTH.md 참고
        },
        body: body === undefined ? undefined : JSON.stringify(body),
    });
}
헤더를 붙이면 바로 201/200이 나옵니다. 백엔드는 정상이고 헤더 누락만 문제입니다.

🔴 2. 전송 버튼에 클릭 핸들러가 없습니다
chat.html:45의 #send-btn은 type="button"이라 폼 제출도 일어나지 않습니다.
JS와 템플릿 전체를 검색해도 sendQuestion()을 부르는 곳은 chat.js:22의 Enter 키 처리뿐입니다.

마우스로 전송이 안 됩니다. docs/FRONTEND.md에는 "전송 버튼: 클릭 시 POST /api/chat 비동기 전송"으로
적혀 있어 문서와도 어긋납니다.

해결
chat.js의 setupInputEvents()에 추가해 주세요.

const sendBtn = document.getElementById('send-btn');
if (sendBtn) sendBtn.addEventListener('click', sendQuestion);
🟠 3. 로그인/회원가입 모달이 화면에 뜰 수 없습니다
pages.py:36-37이 비로그인 /chat 요청을 /login으로 돌려보냅니다.

GET /chat (비로그인) -> 303 -> /login
GET /chat (로그인)   -> 200
즉 chat.html의 #guest-input-overlay, #login-modal, #signup-modal은
비로그인 사용자에게 도달할 수 없습니다. 지금은 A의 /login·/signup 페이지와
이 PR의 모달이라는 두 가지 인증 UX가 공존하는 상태입니다.

어느 쪽으로 갈지 정해야 할 것 같습니다.

모달 방식으로 간다면: pages.py의 /chat 리다이렉트를 없애고 비로그인도 페이지를 받게 해야 합니다.
백엔드 변경이라 A와 조율이 필요합니다.
페이지 방식으로 간다면: chat.html의 모달과 오버레이를 걷어내고 /login 페이지를 채우는 쪽이 낫습니다.
관련해서 login.html, signup.html, history.html에는 아직 JS가 연결되어 있지 않습니다.

🟠 4. 실패를 가짜 AI 답변으로 보여줍니다
chat.js:77 — 네트워크 오류 시

"프론트엔드 mock 응답: "…"에 대한 답변을 준비 중입니다."

docs/FRONTEND.md의 자체 규칙 "아직 없는 API를 성공이나 가짜 AI 답변으로 표시하지 않는다" 와 충돌합니다.
평가나 시연에서 실제 답변으로 오인될 수 있어 오류 문구로 바꾸는 편이 좋겠습니다.

그리고 chat.js:60이 모든 실패의 기본 문구를 (error: AI_TIMEOUT)으로 고정하고 있습니다.
403·401·500도 타임아웃으로 안내됩니다.

PR #22에서 AI 연동이 들어가면 채팅 실패가 상태 코드로 구분됩니다. 처리표를 docs/API.md와
docs/FRONTEND.md에 정리해 뒀습니다.

상태	상황	화면
504	AI 응답 지연	다시 시도 안내
502	AI 연결 실패	다시 시도 안내
500	문맥 조회·저장 실패	detail 그대로 표시
422	빈 입력·1,000자 초과	입력창 옆 표시
401	비로그인·세션 만료	로그인 화면으로
403	X-Requested-With 누락	요청 코드 버그
detail은 그대로 표시해도 되는 문구이며 키나 제공자 오류 상세는 들어 있지 않습니다.
응답에 1초 내외가 걸리므로 로딩 표시는 지금 구조 그대로 유지하시면 좋겠습니다.

🟡 그 외 가벼운 것들
docs/FRONTEND.md v2.0에서 A가 적어둔 X-Requested-With 요구사항이 빠졌습니다.
1번 버그의 뿌리이기도 해서, 문서에 다시 넣어 주시면 좋겠습니다.
auth_sidebar.js:1 주석이 담당자 B로 되어 있는데 프론트는 C 담당입니다.
auth_sidebar.js:54 — 응답 JSON 파싱 실패 시 username: 'demo-user'로 대체합니다.
실패는 실패로 두고 비로그인 UI로 가는 편이 안전합니다.
docs/PR_FIX_LOG_2026-09-20.md — 작업 로그가 저장소에 커밋되어 있습니다.
이런 기록은 PR 본문이 더 적합해 보이고, 내용도 "백엔드 API는 아직 미구현"으로 이미 낡았습니다.
PR 본문 마지막 줄에 "원하면 제가 이걸 더 짧은 GitHub PR용 버전으로 다시 줄여드릴게요." 가 남아 있습니다.
확인한 것
최신 develop + 이 브랜치 로컬 머지: 충돌 없음
백엔드 테스트 100개 통과 (이 PR이 깨뜨리는 것 없음)
위 재현은 모두 실제 서버 응답입니다
1번과 2번은 합쳐서 다섯 줄 정도면 해결됩니다. 3번만 팀 논의가 필요해 보입니다.
필요하시면 수정 패치를 만들어 드리겠습니다.

----------------------------------
## 수정 플랜 (담당 C — 프론트엔드) 2026/09/25

리뷰어(seven2762) 피드백에 대한 프론트엔드 측 수정 계획.

### 사전 작업
- [ ] `feature/frontend` 브랜치에서 최신 `develop`을 머지 또는 리베이스

### 🔴 1. POST 요청 CSRF 헤더 추가 (403 해결)
- [x] 공용 헬퍼 `postJSON(url, body)` 함수 작성
  - `'X-Requested-With': 'XMLHttpRequest'` 헤더 자동 포함
  - `'Content-Type': 'application/json'` 헤더 자동 포함
- [x] `chat.js` — `/api/chat` POST 요청을 `postJSON()` 으로 교체
- [x] `auth_sidebar.js` — `/api/login` POST 요청을 `postJSON()` 으로 교체
- [x] `auth_sidebar.js` — `/api/signup` POST 요청을 `postJSON()` 으로 교체
- [x] `auth_sidebar.js` — `/api/logout` POST 요청을 `postJSON()` 으로 교체

### 🔴 2. 전송 버튼 클릭 이벤트 연동
- [x] `chat.js`의 `setupInputEvents()` 안에 `#send-btn` 클릭 핸들러 추가

### 🟠 3. 인증 방식 (모달 vs 페이지) — 팀 논의 필요
- [ ] PR #20 댓글로 A(백엔드 인증 담당)에게 방향 확인 요청
  - 모달 방식: `pages.py`의 `/chat` 리다이렉트 제거 필요 (백엔드 변경 → A 담당)
  - 페이지 방식: `chat.html`의 모달/오버레이 제거, `/login` 페이지에 JS 연결
- [ ] 결정 후 코드 반영

### 🟠 4. 에러 처리 문구 개선
- [x] `chat.js` catch 블록의 mock 응답 제거 → 실제 오류 문구로 변경
- [x] 상태 코드별 에러 처리 분기 추가 (리뷰어 제공 처리표 기준)
  - 504/502 → 다시 시도 안내
  - 500 → `detail` 그대로 표시
  - 422 → 입력창 옆 표시
  - 401 → 로그인 화면으로
  - 403 → 요청 코드 버그 안내

### 🟡 기타
- [x] `auth_sidebar.js:1` 주석 담당자 B → C로 수정
- [x] `auth_sidebar.js:54` — JSON 파싱 실패 시 `'demo-user'` 대체 제거, 비로그인 UI로 전환
- [x] `docs/FRONTEND.md`에 `X-Requested-With` 요구사항 재추가
- [ ] `docs/PR_FIX_LOG_2026-09-20.md` — PR 본문으로 이동 검토

### 작업 순서
1번 → 2번 → 4번 → 기타 → 커밋 및 푸시 (완료) → 3번은 팀 논의 후 별도 처리