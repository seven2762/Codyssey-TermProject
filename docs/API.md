# API 명세

## 공통

- 기준 주소: FastAPI 서버와 같은 출처. 로컬은 `http://127.0.0.1:8000`.
- JSON 본문: `Content-Type: application/json`.
- 모든 POST: `X-Requested-With: XMLHttpRequest` 필수. GET에는 필요 없음.
- 인증: `askmate_session` 쿠키. 같은 출처의 `fetch`는 쿠키를 자동 전송.
- 세션: HttpOnly, SameSite=Lax. 기본 유효기간 1시간이며 조회로 연장되지 않음.
- 사용자 ID를 전달해 인증·조회 대상을 지정하지 않음.
- 자동 명세: `/docs`, `/openapi.json`.

| 메서드 | 경로 | 로그인 | 성공 응답 |
| --- | --- | --- | --- |
| GET | `/health` | 불필요 | 200, 서버 상태 |
| POST | `/api/signup` | 불필요 | 201, 생성한 사용자 |
| POST | `/api/login` | 불필요 | 200, 사용자 + 세션 쿠키 |
| GET | `/api/me` | 필수 | 200, 현재 사용자 |
| POST | `/api/logout` | 불필요 | 204, 본문 없음 |
| POST | `/api/chat` | 필수 | AI 연동 후 200, 답변. 현재 유효한 요청은 501 |
| GET | `/api/me/chats` | 필수 | 200, 본인 대화 기록 배열 |

## 회원가입 — POST `/api/signup`

| 필드 | 타입 | 조건 |
| --- | --- | --- |
| `username` | string | 필수. 앞뒤 공백 제거·소문자 변환 후 3~30자, 영문·숫자·밑줄 |
| `password` | string | 필수. 15~128자. 공백 포함 원본 그대로 전송 |

요청:

```json
{"username":"demo_user","password":"example password phrase"}
```

201:

```json
{"id":1,"username":"demo_user"}
```

- 자동 로그인되지 않음. 비밀번호 확인은 화면에서 비교하고 API에 보내지 않음.
- 409: `이미 사용 중인 사용자명입니다.`
- 500: `회원가입 정보를 저장하지 못했습니다.`

## 로그인 — POST `/api/login`

| 필드 | 타입 | 조건 |
| --- | --- | --- |
| `username` | string | 필수. 회원가입과 같은 형식 |
| `password` | string | 필수. 1~128자. 공백·대소문자 변환 금지 |

요청:

```json
{"username":"demo_user","password":"example password phrase"}
```

200: `Set-Cookie`로 세션 발급.

```json
{"id":1,"username":"demo_user"}
```

- 401: `사용자명 또는 비밀번호가 올바르지 않습니다.`
- 500: `로그인 정보를 확인하지 못했습니다.`

## 현재 사용자 — GET `/api/me`

본문 없음. 200:

```json
{"id":1,"username":"demo_user"}
```

## 로그아웃 — POST `/api/logout`

- 본문 없음. 현재 브라우저의 세션 쿠키 삭제.
- 204: 응답 본문 없음. `response.json()` 호출 금지.
- 이미 로그아웃된 상태에서도 204.
- 다른 브라우저나 복사된 쿠키를 서버에서 즉시 무효화하지 않음.

## 질문 — POST `/api/chat`

| 필드 | 타입 | 조건 |
| --- | --- | --- |
| `question` | string | 필수. 앞뒤 공백 제거 후 1~1,000자 |

서버가 본인의 최근 5쌍을 오래된 순서의 문맥으로 전달. 이번 질문은 문맥과 별도로 전달.
클라이언트는 사용자 ID나 이전 대화 목록을 보낼 필요 없음.

요청:

```json
{"question":"안녕하세요"}
```

현재 AI 연동 미구현으로 인증·입력 검증을 통과하면 501:

```json
{"detail":"AI 연결이 아직 구현되지 않았습니다."}
```

AI 연동 후 답변 수신·DB 저장 성공 시 200:

```json
{"answer":"안녕하세요! 무엇을 도와드릴까요?"}
```

- 문맥 조회 실패 시 500: `최근 대화 기록을 불러오지 못했습니다.`. AI 호출·새 기록 저장 없음.
- DB 저장 실패 시 500: `대화 기록을 저장하지 못했습니다.`

## 내 대화 기록 — GET `/api/me/chats`

- 본문 없음. 본인의 전체 기록을 `created_at DESC, id DESC` 순서로 반환.
- `created_at`: UTC ISO 8601 문자열. 소수점 이하 초가 포함될 수 있음.
- 기록이 없으면 200과 `[]`.

200:

```json
[
  {
    "id":1,
    "question":"안녕하세요",
    "answer":"안녕하세요!",
    "created_at":"2026-09-20T03:00:00Z"
  }
]
```

- 500: `대화 기록을 불러오지 못했습니다.`

## 서버 상태 — GET `/health`

200:

```json
{"status":"ok"}
```

DB·외부 AI 연결 상태는 검사하지 않음.

## 공통 오류·캐시

일반 오류는 `detail` 문자열. 각 API의 오류 메시지는 이 필드로 반환.

```json
{"detail":"로그인이 필요합니다."}
```

| 코드 | 발생 조건 | `detail` |
| --- | --- | --- |
| 401 | 로그인 필수 API의 세션 없음·만료·변조 | `로그인이 필요합니다.` |
| 403 | POST 공통 헤더 누락·오류 | `X-Requested-With: XMLHttpRequest 헤더가 필요합니다.` |
| 422 | 필수 필드 누락·타입·길이·형식 오류 | 검증 오류 배열 |
| 500 | 로그인 필수 API에서 세션 사용자 DB 조회 실패 | `로그인 정보를 확인하지 못했습니다.` |

422 예시:

```json
{"detail":[{"type":"string_too_short","loc":["body","username"],"msg":"String should have at least 3 characters"}]}
```

`loc`는 오류 필드, `msg`는 안내 메시지. 원본 입력과 비밀번호는 반환하지 않음.
로그인·로그아웃·현재 사용자·대화 기록의 성공 응답은 `Cache-Control: no-store`.
