# 프론트엔드 담당 커밋 파일 개요 및 상세 정리

- **작성자**: nttkor (`nttkor@gmail.com`)
- **담당 역할**: 프론트엔드 개발 (담당 C)
- **정리 일자**: 2026-09-25

---

## 1. 커밋 이력 요약

| 일시 | 커밋 해시 | 커밋 메시지 | 변경 파일 |
|---|---|---|---|
| **09-20** | `51f6121` | docs: FRONTEND.md 기술 명세서 v2.0 개선안 반영 | `docs/FRONTEND.md` |
| **09-20** | `76e5665` | feat: 제미나이 스타일 2-Pane 레이아웃 및 모달 HTML 뼈대 구조화 | `backend/app/templates/chat.html` |
| **09-20** | `288a60c` | style: 메인 대화창 말풍선, 비로그인 오버레이 및 팝업 모달 CSS 스타일링 | `backend/app/static/css/style.css` |
| **09-20** | `9be71b4` | feat: 질문 전송, 1000자 제한 검증 및 XSS 방지 로직 구현 | `backend/app/static/js/chat.js` |
| **09-20** | `a87f01b` | feat: 인증 상태 확인, 로그인 모달 제어 및 사이드바 대화 기록 연동 | `backend/app/static/js/auth_sidebar.js` |
| **09-20** | `8cf2cc6` | docs:frontend v2 bug fix | `docs/PR_FIX_LOG_2026-09-20.md` |
| **09-20** | `b7fb5f8` | feat: frontend chat UI and auth modal flow | `chat.html`, `chat.js`, `auth_sidebar.js`, `PR_FIX_LOG` |
| **09-25** | `f2b215d` | docs: 리뷰어 피드백 및 프론트엔드 수정 계획 추가 | `docs/FRONTEND.md` |
| **09-25** | `2716d9f` | fix: 채팅 전송 버튼(#send-btn) 클릭 이벤트 핸들러 연동 | `backend/app/static/js/chat.js` |
| **09-25** | `e477693` | fix: POST 요청 시 CSRF 방어용 X-Requested-With 헤더 전송 헬퍼 적용 | `backend/app/static/js/chat.js`, `auth_sidebar.js` |
| **09-25** | `603e661` | fix: mock 응답 제거 및 HTTP 상태 코드별 대화 에러 메시지 분기 처리 | `backend/app/static/js/chat.js` |
| **09-25** | `948001b` | refactor: 인증 상태 파싱 예외 처리 보완 및 프론트 담당자 표기 수정 | `backend/app/static/js/auth_sidebar.js` |
| **09-25** | `f737e89` | docs: 피드백 반영 체크리스트 갱신 및 문서 정리 | `docs/FRONTEND.md` |

---

## 2. 파일별 개요 및 상세 구현 내용

### 1) `backend/app/templates/chat.html`
- **개요**: Gemini/ChatGPT 스타일의 2-Pane 레이아웃(좌측 사이드바 + 우측 채팅 메인)과 비로그인 게스트 오버레이, 로그인/회원가입 팝업 모달을 포함한 단일 메인 뷰 템플릿.
- **상세 내용**:
  - **좌측 사이드바 (`<aside class="sidebar">`)**:
    - `+ 새 대화 시작` 버튼 (`#new-chat-btn`)
    - 최근 대화 목록 렌더링 컨테이너 (`#history-list`)
    - 하단 사용자 프로필 및 로그인/로그아웃 링크 영역 (`#user-profile-area`)
  - **우측 대화창 메인 (`<main class="chat-main">`)**:
    - 헤더 접속 상태 표시 (`#header-user-status`)
    - 대화 메시지 목록 스크롤 박스 (`#chat-box`) 및 초기 안내 웰컴 카드 (`#welcome-card`)
    - 입력창 영역:
      - 비로그인 시 입력창을 덮고 클릭 시 로그인 모달을 띄우는 게스트 오버레이 (`#guest-input-overlay`)
      - 1,000자 제한 텍스트영역 (`#chat-input`)
      - 실시간 글자 수 카운터 (`#char-counter`)
      - 전송 버튼 (`#send-btn`)
  - **모달 컴포넌트**:
    - 로그인 모달 (`#login-modal`): 아이디/비밀번호 입력 폼 및 회원가입 모달 전환 링크
    - 회원가입 모달 (`#signup-modal`): 아이디/비밀번호/비밀번호 확인 폼 및 에러 메시지 박스
  - **스크립트 연결**: `chat.js`와 `auth_sidebar.js`를 `defer` 속성으로 로드.

---

### 2) `backend/app/static/css/style.css`
- **개요**: 전체 화면 2-Pane 레이아웃, 메시지 말풍선, 비로그인 오버레이, 팝업 모달을 담당하는 전역 스타일시트.
- **상세 내용**:
  - **전체 레이아웃**:
    - `.app-container`: Flexbox 기반 `100vh` 높이 및 뷰포트 스크롤 방지 (`overflow: hidden`).
    - `.sidebar`: 고정 폭(260px)과 배경색 구분.
    - `.chat-main`: 화면 나머지 너비를 차지하는 유연 확장 구조 (`flex: 1`).
  - **말풍선 디자인**:
    - 사용자 말풍선 (`.message-row.user`): 우측 정렬, 블루 배경 (`#0b57d0`), 화이트 텍스트.
    - AI 말풍선 (`.message-row.ai`): 좌측 정렬, 연그레이 배경 (`#f0f4f9`).
    - 에러 말풍선 (`.bubble.error-bubble`): 연붉은 경고 배경 (`#fce8e6`), 붉은 에러 텍스트 (`#c5221f`).
  - **UI/상태 피드백**:
    - 게스트 오버레이 (`.guest-overlay`): 반투명 화이트 배경(`rgba(255, 255, 255, 0.85)`)으로 비활성 입력창을 덮고 클릭 유도.
    - 버튼 비활성화 상태 (`.btn-send:disabled`), 폼 유효성 에러 강조 (`.input-error`), 모달 오버레이 (`.modal-overlay`) 딤 처리.

---

### 3) `backend/app/static/js/chat.js`
- **개요**: 채팅 입력, 글자 수 제한, 전송(버튼 및 Enter), 로딩 표시, HTTP 상태 코드별 에러 처리, 메시지 DOM 렌더링을 담당하는 클라이언트 스크립트.
- **상세 내용**:
  - **공용 CSRF 전송 헬퍼**:
    - `postJSON(url, body)` 함수를 정의하여 모든 POST 요청 시 CSRF 방어용 필수 헤더 `X-Requested-With: XMLHttpRequest` 및 `Content-Type: application/json` 자동 전송.
  - **입력 이벤트 및 전송 연동**:
    - 실시간 입력 길이 감지 및 1,000자 초과 시 자동 자르기/카운터 업데이트 (`#char-counter`).
    - Enter 키 전송 (Shift+Enter는 줄바꿈 허용).
    - 전송 버튼 (`#send-btn`) 클릭 이벤트 핸들러 바인딩.
  - **채팅 흐름 및 렌더링**:
    - 공백 입력 차단, 질문 전송 시 로딩 메시지(임시 고유 ID 부여) 표시 및 자동 하단 스크롤 (`scrollToBottom()`).
    - `textContent`를 사용한 메시지 삽입으로 **XSS(크로스 사이트 스크립팅) 취약점 방지**.
  - **에러 핸들링 고도화**:
    - 과거 catch 블록의 mock 응답 제거 → 실제 네트워크 장애 안내.
    - `handleChatError(status, errData)` 함수로 HTTP 응답 상태 코드별 세부 분기:
      - **504 / 502**: AI 응답 지연 또는 연결 실패 안내 (재시도 유도).
      - **500**: 서버 내부 오류 메시지 (`detail`) 그대로 표출.
      - **422**: 입력값 검증 실패 안내.
      - **401**: 인증 만료/미인증 시 로그인 모달 (`openModal('login-modal')`) 자동 호출.
      - **403**: CSRF 헤더 누락/차단 관련 페이지 새로고침 안내.

---

### 4) `backend/app/static/js/auth_sidebar.js`
- **개요**: 세션 기반 인증 상태 확인(`GET /api/me`), 모달 제어(로그인/회원가입), 로그아웃, 최근 대화 히스토리 목록 렌더링을 담당하는 스크립트.
- **상세 내용**:
  - **인증 상태 동기화 (`checkAuthStatus`)**:
    - 페이지 로드 시 `/api/me`를 호출하여 로그인 상태 확인.
    - JSON 파싱 예외 발생 시 더미 계정(`demo-user`)을 주입하던 기존 취약점을 제거하고 안전하게 비로그인 UI(`setGuestUI()`)로 전환.
  - **동적 UI 전환**:
    - `setLoggedInUI(username)`: 사용자 헤더 표시, 로그아웃 링크 생성, 게스트 오버레이 숨김, 입력창/전송버튼 활성화, 대화 기록 인덱스 로딩.
    - `setGuestUI()`: 비로그인 상태 표기, 입력창 비활성화, 게스트 오버레이 노출.
  - **모달 및 폼 제출 핸들링**:
    - 로그인/회원가입 모달 열기/닫기/상호 전환 (`switchModal`).
    - `postJSON()`을 활용한 `/api/login`, `/api/signup`, `/api/logout` 요청 처리.
    - 회원가입 시 비밀번호 일치 검증 및 백엔드 4xx/5xx 에러 메시지(`detail`) 추출 노출.
  - **사이드바 대화 목록 (`loadHistoryIndex`)**:
    - `/api/me/chats`를 호출하여 최신 대화 목록 렌더링.
    - 히스토리 아이템 클릭 시 본문 대화창에 해당 질문과 답변 복원 표시.

---

### 5) `docs/FRONTEND.md`
- **개요**: 프론트엔드 아키텍처 및 구현 명세서, API 규격, 리뷰어 피드백 대응 체크리스트를 관리하는 문서.
- **상세 내용**:
  - Jinja2 + 순수 HTML/CSS/JavaScript 구조 명세 및 화면별 역할 정의.
  - POST 요청 시 CSRF 방어용 `X-Requested-With: XMLHttpRequest` 필수 헤더 규격 명시.
  - 리뷰어 피드백 대응 체크리스트(CSRF 헤더 추가, 전송 버튼 이벤트 연동, 에러 메시지 분기, 주석 담당자 표기 수정 등) 갱신 및 완료 상태 추적.

---

### 6) `docs/PR_FIX_LOG_2026-09-20.md`
- **개요**: 프론트엔드 v2 구현 시점의 이슈와 조치 내역을 기록한 로그 문서.
- **상세 내용**: DOM 식별자 불일치 해결, 문자열 escape 로직 보안 조치, 백엔드 API 연동 전 템플릿/UI 검증 내역 기록.

---

## 3. 핵심 개선 및 성과 요약

1. **보안성 강화**:
   - `postJSON` 헬퍼 도입으로 백엔드의 엄격한 CSRF 검사(`X-Requested-With`) 100% 대응.
   - 메시지 삽입 시 `textContent`를 일관되게 적용하여 XSS 차단.
   - 인증 실패/파싱 에러 시 비정상적인 세션 진입 차단 (게스트 상태로 안전 회귀).
2. **사용자 경험(UX) 및 인터랙션 개선**:
   - 질문 전송 버튼(`#send-btn`) 클릭 핸들러 연동 누락 수정.
   - 실시간 1,000자 입력 제한 카운터 및 비로그인 시 직관적인 모달 호출 게스트 오버레이 적용.
3. **견고한 예외 처리**:
   - 이전의 mock 응답 의존성을 완전 제거하고, HTTP 504/502/500/422/401/403에 맞춘 상태별 에러 메시지 분기 로직 구축.
