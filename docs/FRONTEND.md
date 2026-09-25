# AskMate 프론트엔드 문서

## 문서 변경 이력

| 작성일자 | 버전 | 작성자 | 주요 변경 및 개선 내용 |
| :--- | :--- | :--- | :--- |
| 2026-09-17 | v1.0 | 프론트엔드팀 | 초안 작성 (기본 화면 구성 및 라우팅 정의) |

## 프론트 작업 안내 (C 담당)

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

```
# 🎨 AskMate 프론트엔드 UI/UX 및 기술 명세서 (FRONTEND.md)

## 📜 문서 변경 이력 (Revision History)
| 작성일자 | 버전 | 작성자 | 주요 변경 및 개선 내용 |
| :--- | :--- | :--- | :--- |
| 2026-09-20 | v2.0 | 프론트엔드팀 | [개선안] 제미나이 2-Pane 레이아웃, 모달 팝업, /api/* 엔드포인트 통일, 204/422 예외 처리 및 2인 HTML/JS 파일 분리 반영 |

---

## 📁 프로젝트 내 실제 저장 위치 안내
| 구분 | 파일 경로 | 담당 및 내용 |
| :--- | :--- | :--- |
| **기획/기술 문서** | `docs/FRONTEND.md` | 프론트엔드 기획, UI/UX 사양, 2인 협업 및 API 연동 명세 |
| **HTML 템플릿** | `backend/app/templates/chat.html` | 메인 대화창 뼈대 및 Jinja2 `include` 통합 |
| | `backend/app/templates/sidebar.html` | **담당자 B**: 좌측 사이드바 HTML 조각 (`{% include %}`) |
| | `backend/app/templates/modal.html` | **담당자 B**: 로그인 / 회원가입 팝업 모달 HTML 조각 (`{% include %}`) |
| **CSS 스타일시트** | `backend/app/static/css/style.css` | 전체 UI/UX, 말풍선, 오버레이, 모달 디자인 |
| **JS 스크립트 (A)** | `backend/app/static/js/chat.js` | **담당자 A**: 메인 채팅, 질문 전송, 글자 수 검증, 자동 스크롤 |
| **JS 스크립트 (B)** | `backend/app/static/js/auth_sidebar.js` | **담당자 B**: 인증 상태, 로그인/가입 모달, 사이드바 대화 기록 |

---

## 1. 개요 및 UI/UX 설계 철학
* **서비스명**: AskMate (로그인 기반 범용 AI 챗봇 웹 서비스)
* **디자인 컨셉**: **제미나이(Gemini) 스타일의 2-Pane 레이아웃** (좌측 사이드바 + 우측 메인 대화창)
* **핵심 UX 목표**:
  * 별도의 페이지 이동(`/history` 등) 없이 단일 대화 화면(`/chat`)에서 대화 생성, 과거 기록 조회, 회원가입/로그인(모달)을 모두 수행하는 단일 페이지(SPA) 경험 제공.
  * 로그인/비로그인 상태에 따라 기능 접근 권한을 동적으로 제어하여 기말 평가 기준(비로그인 시 챗 기능 불가) 완벽 충족.

---

## 2. ASCII 텍스트 와이어프레임 (UI Layout)

```text
+----------------------------------------------------------------------------------------------------+
|                                      [ AskMate 웹 서비스 UI ]                                       |
+------------------------------------+---------------------------------------------------------------+
|  <aside>           |  <main>                                     |
|                                    |                                                               |
|  +------------------------------+  |  +---------------------------------------------------------+  |
|  |  + 새 대화 시작              |  |  |  AskMate AI  (Gemini Flash v1)          [사용자: 65ntt]  |  |
|  +------------------------------+  |  +---------------------------------------------------------+  |
|                                    |  |                                                         |  |
|  [ 이전 대화 목록 ]                |  |  <div>                                    |  |
|  +------------------------------+  |  |                                                         |  |
|  | 💬 배포 방법 문의            |  |  |  [User]                                                 |  |
|  | 💬 FastAPI 라우터 구조      |  |  |  +---------------------------------------------------+  |  |
|  | 💬 SQLite DB 모델링          |  |  |  | 배포는 어떻게 하나요?                             |  |  |
|  | 💬 최근 대화 문맥 연동       |  |  |  +---------------------------------------------------+  |  |
|  | 💬 회원가입 기능 검증        |  |  |                                                         |  |
|  +------------------------------+  |  |  [AskMate AI]                                           |  |
|                                    |  |  +---------------------------------------------------+  |  |
|  (스크롤 가능한 목록 영역)         |  |  | Docker 이미지 생성 후 OCI Compute 인스턴스에       |  |  |
|                                    |  |  | Tailscale을 통해 배포합니다.                      |  |  |
|                                    |  |  +---------------------------------------------------+  |  |
|                                    |  |                                                         |  |
|                                    |  |  [AskMate AI - 상태/에러 예시]                          |  |
|                                    |  |  +---------------------------------------------------+  |  |
|  +------------------------------+  |  |  | ⏳ AI가 답변을 생성하는 중입니다...               |  |  |
|  | 👤 65ntt [로그아웃]          |  |  |  | ⚠️ 현재 응답이 지연되고 있습니다. (AI_TIMEOUT)   |  |  |
|  +------------------------------+  |  |  +---------------------------------------------------+  |  |
|                                    |  |  </div>                                                 |  |
|                                    |  |                                                         |  |
|                                    |  |  +---------------------------------------------------------+  |
|                                    |  |  |                    |  |
|                                    |  |  |                                                         |  |
|                                    |  |  |  [0 / 1,000자]                              [전송 ↵]   |  |
|                                    |  |  +---------------------------------------------------------+  |
+------------------------------------+---------------------------------------------------------------+

```

---

## 3\. 화면 컴포넌트 및 상세 UI 사양

### 3.1\. 좌측 사이드바 (`<aside>`)

* **상단 헤더**: `+ 새 대화 시작` 버튼 (`#new-chat-btn`, `.btn-primary`). 클릭 시 대화창을 초기화하고 환영 카드를 새로 출력.
* **중앙 인덱스 영역 (** **#history-list** **)**: `GET /api/me/chats` 연동 대화 목록.
  * 로그인 시: 사용자의 과거 질문 요약 항목 렌더링. 클릭 시 대화내용 대화창에 복원.
  * 비로그인 시: "로그인 후 기록 확인 가능" 안내 메시지 표시.
* **하단 프로필 영역 (** **#user-profile-area** **)**:
  * 로그인 시: `👤 {username}` 및 `[로그아웃]` 링크 표시 (`POST /api/logout` 연동).
  * 비로그인 시: "로그인이 필요합니다" 문구 및 `[로그인]` 버튼 배치 (로그인 모달 오픈).

### 3.2\. 우측 메인 대화 영역 (`<main>`)

* **상단 헤더 (** **.chat-header** **)**: 서비스 로고(`AskMate AI`) 및 현재 접속 상태(`{username}님 접속 중` / `비로그인 상태`).
* **대화창 (** **#chat-box** **)**:
  * **초기 상태**: 환영 안내 카드 (`.welcome-card`).
  * **사용자 말풍선**: 우측 정렬, 파란색 배경 (`#0b57d0`), 흰색 글씨. `textContent`로 XSS 방지.
  * **AI 말풍선**: 좌측 정렬, 연회색 배경 (`#f0f4f9`), 검은색 글씨. `textContent`로 XSS 방지.
  * **상태/로딩 표시**: AI 응답 대기 중 "⏳ AI가 답변을 생성하는 중입니다..." 출력.
  * **자동 스크롤**: 새 메시지 전송 및 수신 시 대화창 최하단으로 자동 이동 (`scrollTop = scrollHeight`).

### 3.3\. 하단 질문 입력 영역 (`.chat-input-container`)

* **비로그인 오버레이 (** **#guest-input-overlay** **)**: 비로그인 시 입력창 위를 반투명으로 덮어 클릭을 차단하고, 클릭 시 로그인 팝업 모달을 오픈.
* **질문 입력창 (** **#chat-input** **)**: `textarea` 폼. **1,000자 제한**, 공백 입력 차단, Enter 전송 (Shift+Enter 줄바꿈).
* **하단 바 (** **.input-bottom-bar** **)**: 실시간 글자 수 카운터 (`#char-counter`, `0 / 1,000자`) 및 `[전송]` 버튼 (`#send-btn`).

### 3.4\. 인증 및 가입 팝업 모달 (`#login-modal`, `#signup-modal`)

* **로그인 모달**: 아이디 (`#login-username`), 비밀번호 (`#login-password`) 입력 필드, 로그인 실패 시 에러 상자 (`#login-error-msg`), 회원가입 모달 전환 링크.
* **회원가입 모달**: 아이디 (`#signup-username`), 비밀번호 (`#signup-password`), 비밀번호 확인 (`#signup-password-confirm`) 필드, 에러 상자 (`#signup-error-msg`).

---

## 4\. UI 컴포넌트 명세 및 역할 분담

| 구역            | 컴포넌트명          | HTML / JS 파일                       | 핵심 기능 및 JavaScript 연동 로직                                   |
| ------------- | -------------- | ---------------------------------- | ---------------------------------------------------------- |
| **사이드바 (좌)**  | **새 대화 버튼**    | `sidebar.html` / `chat.js`         | 클릭 시 메인 대화창 초기화 및 환영 카드 출력                                 |
|               | **대화 목록 인덱스**  | `sidebar.html` / `auth_sidebar.js` | `GET /api/me/chats` 연동. 클릭 시 이전 대화 내역 메인창 복원               |
|               | **프로필 &amp; 로그아웃** | `sidebar.html` / `auth_sidebar.js` | 로그인 상태에 따라 사용자 ID 및 로그아웃(`POST /api/logout`) 제어            |
| **메인 영역 (우)** | **채팅 헤더**      | `chat.html` / `auth_sidebar.js`    | 서비스명(`AskMate AI`) 및 사용자 접속 상태 동적 표시                       |
|               | **대화 말풍선 영역**  | `chat.html` / `chat.js`            | User(우측)/AI(좌측) 말풍선 출력, `textContent`로 XSS 방지 및 자동 최하단 스크롤 |
|               | **비로그인 오버레이**  | `chat.html` / `auth_sidebar.js`    | 비로그인 시 입력창 차단 오버레이 표시 및 클릭 시 로그인 모달 오픈                     |
|               | **질문 입력창**     | `chat.html` / `chat.js`            | 1,000자 제한, 공백 입력 차단, Enter 키 전송 (Shift+Enter 줄바꿈)          |
|               | **글자 수 카운터**   | `chat.html` / `chat.js`            | `input` 이벤트 감지를 통해 실시간 `0 / 1,000자` 표시                     |
|               | **전송 버튼**      | `chat.html` / `chat.js`            | 클릭 시 `POST /api/chat` 비동기(`fetch`) 전송                      |

---

## 5\. 비로그인 및 예외/오류 처리 UX 규칙

| 발생 상황              | 백엔드 상태코드               | 화면/UI 반응                                   | 사용자 안내 메시지 / 처리 로직                                      |
| ------------------ | ---------------------- | ------------------------------------------ | ------------------------------------------------------- |
| **비로그인 사용자 접근**    | \-                     | 입력창 비활성화(`disabled`), 오버레이 표시              | `🔒 질문을 입력하려면 로그인이 필요합니다. (클릭하여 로그인)`                   |
| **로그인 인증 실패**      | HTTP 401 Unauthorized  | 비밀번호 필드 붉은 테두리 강조 (`.input-error`), 포커스 이동 | `⚠️ 아이디 또는 비밀번호가 올바르지 않습니다.`                            |
| **입력값 검증 오류**      | HTTP 422 Unprocessable | 422 `detail` 배열 파싱 후 에러 상자 출력              | `⚠️ 아이디와 비밀번호를 모두 입력해 주세요.` / `⚠️ 비밀번호가 일치하지 않습니다.`     |
| **로그아웃 성공**        | HTTP 204 No Content    | 세션 초기화 및 비로그인 UI 전환                        | 204 응답 시 JSON 파싱하지 않고 비로그인 상태로 화면 전환                    |
| **AI API 타임아웃/오류** | HTTP 504 / 500         | 붉은색 에러 말풍선 출력 (`.error-bubble`)            | `현재 응답이 지연되고 있어요. 잠시 후 다시 시도해 주세요. (error: AI_TIMEOUT)` |

---

## 6\. 백엔드 API 연동 규격 (Fetch API)

1. **로그인 상태 확인**: `GET /api/me`
   - 성공 시 로그인 UI 전환 및 이전 대화 목록 불러오기 실행
2. **로그인**: `POST /api/login`
   - Body: `{ "username": "...", "password": "..." }`
   - 실패 시 401/422 에러 메시지 동적 모달 출력
3. **회원가입**: `POST /api/signup`
   - Body: `{ "username": "...", "password": "..." }`
4. **로그아웃**: `POST /api/logout`
   - Response: 204 No Content (JSON 파싱 방지)
5. **AI 질문 전송**: `POST /api/chat`
   - Body: `{ "question": "..." }` \-&gt; Response: `{ "answer": "..." }`
6. **이전 대화 목록 조회**: `GET /api/me/chats`
   - Response: `[ { "id": 1, "question": "...", "answer": "...", "created_at": "..." } ]`

---

## 7\. 프론트엔드 2인 협업 및 파일 분리 구조

* **충돌 방지 설계**: HTML 템플릿(`sidebar.html`, `modal.html`)과 자바스크립트(`chat.js`, `auth_sidebar.js`)를 완전히 분리하여 작업함으로써 Git Merge Conflict 0% 달성.
* **담당자 A (** **chat.js** **&amp;** **chat.html** **메인 영역)**:
  * 우측 메인 채팅 레이아웃, 말풍선 생성, 질문 전송, 1,000자 제한 입력 검증, 자동 최하단 스크롤, `POST /api/chat` 연동.
* **담당자 B (** **auth\_sidebar.js** **&amp;** **sidebar.html** **,** **modal.html** **)**:
  * 사용자 인증 상태 관리 (`GET /api/me`), 로그인/회원가입 팝업 모달 제어 및 401/422 예외 처리, 사이드바 이전 대화 목록 (`GET /api/me/chats`) 연동.
* **Git 브랜치 전략**: `feature/frontend-ui` (담당자 A) 및 `feature/frontend-auth` (담당자 B) 브랜치에서 작업 후 `develop` 브랜치로 PR 제출, 팀원 코드 리뷰 후 Merge.</main></aside></main></aside>