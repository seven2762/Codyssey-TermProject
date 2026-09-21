# LLM 작업 안내 (B 담당)

## 파일별 역할

| 파일 | 역할 |
| --- | --- |
| `backend/app/llm.py` | HTTP 요청·응답, 인증 연결, 최근 대화 조회, 답변 저장, HTTP 오류 변환 |
| `backend/app/llm_connect.py` | B가 실제 수정할 외부 AI 통신 모듈. 요청 구성·타임아웃·응답 추출 |
| `backend/app/config.py` | 공통 환경변수 읽기. AI 설정을 추가할 때 사용 |
| `backend/app/models/chat.py` | 구현된 대화 기록 모델 |
| `backend/app/chat_db.py` | 저장 `create_chat()`, 전체 조회 `get_chats_by_user()`, 문맥 조회 `get_recent_chats_by_user()` |

호출 흐름은 `화면 → POST /api/chat → llm.py → llm_connect.generate_answer() → AI 서비스`이다.
외부 AI 키나 SDK를 프론트에서 사용하지 않는다.

## 현재 연결 상태

`llm.py`는 `Depends(get_current_user)`로 인증한 사용자의 질문만 통신 함수로 전달한다.
질문 앞뒤 공백을 제거하고 1~1,000자로 검증한다.
`generate_answer()`는 OpenAI 호환 게이트웨이에 Chat Completions 형식으로 요청한다.
최근 5쌍의 문맥 조회·전달, 답변 수신 후 저장, 본인 기록 조회 API가 연결되어 있다.

## 환경 변수

| 변수 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `AI_API_KEY` | 예 | 없음 | 게이트웨이 API 키. `Authorization: Bearer`로 전송한다 |
| `AI_BASE_URL` | 예 | 없음 | 게이트웨이 주소. `/chat/completions` 앞까지 적는다 |
| `AI_MODEL` | 예 | 없음 | 사용할 모델 이름 |
| `AI_TIMEOUT` | 아니오 | `30` | 응답 제한 시간(초). 양수 |

## 게이트웨이와 모델

학교에서 제공하는 OpenAI 호환 게이트웨이 `https://copa.codyssey.kr/v1`을 사용한다.
키는 이 게이트웨이에서 발급한 값이며, `Authorization: Bearer`로 전송한다.

사용 가능한 모델은 아래 명령으로 확인한다.

```bash
curl -H "Authorization: Bearer $AI_API_KEY" https://copa.codyssey.kr/v1/models
```

기본값은 `gpt-5.4-mini`이다. 응답이 1초 내외로 빠르고 일상 질문에 충분하다.

| 모델 | 상태 | 참고 |
| --- | --- | --- |
| `gpt-5.4-mini` | 사용 가능 | 현재 기본값 |
| `gpt-5.4`, `gpt-5.5`, `gpt-5-mini` | 사용 가능 | |
| `gemini-3.1-flash-lite`, `gemini-3-flash`, `gemini-3.1-pro` | 사용 가능 | `gemini-3.1-pro`는 약 5초로 느리다 |
| `claude-haiku-4`, `claude-sonnet-4`, `claude-opus-4-7`, `claude-opus-4-8` | **사용 불가** | 현재 키로 호출하면 400 `Invalid request` |

모델을 바꾸려면 코드 수정 없이 `AI_MODEL` 값만 변경한다.
배포 환경은 `production` 환경 Variable로 설정한다.

`config.py`가 기동 시점에 검증하므로, 값이 없거나 형식이 틀리면 앱이 시작하지 않는다.
첫 질문에서가 아니라 배포 단계에서 설정 오류를 알 수 있다.
배포 환경의 등록 방법은 [OCI Docker 배포](DEPLOYMENT.md)를 따른다.

## 오류 처리

| 상황 | 예외 | HTTP | 사용자 응답 |
| --- | --- | --- | --- |
| 제한 시간 초과 | `AITimeoutError` | 504 | AI 응답이 지연되어 답변을 받지 못했습니다… |
| 제공자 오류·연결 실패·빈 답변 | `AIServiceError` | 502 | AI 서비스에 연결하지 못했습니다… |
| 최근 문맥 조회 실패 | `SQLAlchemyError` | 500 | 최근 대화 기록을 불러오지 못했습니다. |
| 대화 저장 실패 | `SQLAlchemyError` | 500 | 대화 기록을 저장하지 못했습니다. |

제공자가 돌려준 오류 본문에는 키나 내부 정보가 섞일 수 있으므로 사용자 응답에 넣지 않는다.
실패한 질문은 저장하지 않으며, 다음 요청의 문맥에도 포함되지 않는다.
`max_retries=0`이므로 SDK가 자동으로 재시도하지 않는다. 재시도는 사용자가 다시 질문해 수행한다.

## 로그

| 이벤트 | 남기는 값 |
| --- | --- |
| `ai_call_started` | 모델, 메시지 개수, 제한 시간 |
| `ai_call_success` | 모델, 소요 시간, 답변 길이 |
| `ai_call_timeout` | 모델, 소요 시간 |
| `ai_call_failure` | 모델, 소요 시간, 예외 종류 |
| `ai_failure` | 사용자 ID, 실패 사유(`timeout`·`service`) |

API 키와 질문·답변 본문은 기록하지 않는다. 길이와 예외 종류만 남긴다.

서버에 테스트 계정을 가입한 뒤 아래처럼 로그인하고 연결을 확인한다.
`.env`와 계정 API 설정은 [인증 안내](AUTH.md)를 따른다.
쿠키 파일에는 로그인 정보가 있으므로 임시 파일을 사용하고 확인 후 삭제한다.
인증과 입력 검증을 통과한 경우의 501은 현재 의도한 결과이다.

```bash
askmate_cookie_file=$(mktemp)
curl -i -c "$askmate_cookie_file" http://127.0.0.1:8000/api/login \
  -H 'Content-Type: application/json' \
  -H 'X-Requested-With: XMLHttpRequest' \
  -d '{"username":"demo_user","password":"example password phrase"}'
curl -i http://127.0.0.1:8000/api/chat \
  -b "$askmate_cookie_file" \
  -H 'Content-Type: application/json' \
  -H 'X-Requested-With: XMLHttpRequest' \
  -d '{"question":"안녕하세요"}'
rm "$askmate_cookie_file"
```

함수 규격은 다음처럼 유지한다.

```python
async def generate_answer(question: str, history: list[dict[str, str]]) -> str:
    ...
```

- `question`: 이번 질문. history에 중복해서 넣지 않는다.
- `history`: 현재 사용자의 최근 5개 질문·답변 쌍을 오래된 순서로 펼친 메시지 목록.
  각 항목은 `{"role":"user","content":"질문"}` 또는 `{"role":"assistant","content":"답변"}`이다.
  최대 10개 메시지이며, 기록이 없으면 빈 목록이다. 같은 시각의 기록은 ID 순서로 정렬한다.
- 반환값: AI 답변 문자열. HTTP 응답 객체나 DB 모델을 반환하지 않는다.
- 라우터가 로그인 사용자의 DB 기록으로 history를 구성한다. 요청 본문의 `user_id`나 `history`는 사용하지 않는다.
- B는 전달받은 history 뒤에 이번 question을 한 번 추가해 AI 요청을 구성한다. DB 조회를 다시 구현하지 않는다.

## 구현 내용

1. `openai` SDK를 `uv add`로 추가했다. OpenAI 호환 게이트웨이를 `base_url`로 지정한다.
2. `config.py`에 AI 키·주소·모델·제한 시간을 추가하고 기동 시점에 검증한다.
3. `llm_connect.py`에서 `AsyncOpenAI`로 비동기 호출하며 `AI_TIMEOUT`을 적용한다.
   요청마다 연결을 새로 맺지 않도록 클라이언트를 모듈 수준에서 재사용한다.
4. 기존 `get_current_user`·`require_csrf_header` 연결을 유지했다.
5. 전달받은 최근 5쌍의 history 뒤에 이번 question을 한 번만 덧붙여 요청을 만든다.
6. 기존 `create_chat()` 호출을 유지했다. 중복 저장을 추가하지 않았다.

저장은 `llm.py`가 `run_in_threadpool()`로 실행하고 완료될 때까지 기다린다.
`llm_connect.py`는 DB를 다루지 않고 답변 문자열만 반환한다.
문맥 조회도 스레드에서 실행한다. 조회 실패는 500과 `최근 대화 기록을 불러오지 못했습니다.`로
안내하며 `db_read_failure operation=chat_context`를 기록한다. 이때 AI 호출·저장은 하지 않는다.

POST 공통 헤더 누락·오류는 403, 인증 실패는 401, 인증 후 입력 검증 실패는 422로 처리한다.
DB 저장 실패는 rollback하고 성공 응답 대신 500과 저장 실패 안내를 반환한다.
AI를 기다리는 동안 DB 쓰기 트랜잭션을 열어두지 않는다.

## 작업 완료 확인

`backend/tests/test_ai_chat.py`가 로컬 HTTP 서버를 게이트웨이로 띄워 아래를 확인한다.

- 미로그인·입력 검증 실패 요청은 게이트웨이를 호출하지 않는다.
- 요청 경로·`Authorization` 헤더·`model`·`messages`가 Chat Completions 형식을 따른다.
- 이전 질문에 이어서 대화할 수 있고 이번 질문이 중복으로 들어가지 않는다.
- 타임아웃은 504, 제공자 오류·빈 답변은 502로 응답하고 저장하지 않는다.
- 실패 응답과 로그에 API 키나 제공자 오류 상세가 들어가지 않는다.
- 실패 이후 다음 요청이 정상 처리된다.
- 성공한 질문·답변이 저장되고 `GET /api/me/chats`에서 본인 기록으로 확인된다.
