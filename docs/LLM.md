# LLM 작업 안내 (B 담당)

## 파일별 역할

| 파일 | 역할 |
| --- | --- |
| `backend/app/llm.py` | HTTP 요청·응답, 인증 연결, 최근 대화 조회, 답변 저장, HTTP 오류 변환 |
| `backend/app/llm_connect.py` | B가 실제 수정할 외부 AI 통신 모듈. 요청 구성·타임아웃·응답 추출 |
| `backend/app/config.py` | 공통 환경변수 읽기. AI 설정을 추가할 때 사용 |
| `backend/app/models/chat.py` | D가 정의할 대화 기록 모델 |

호출 흐름은 `화면 → POST /api/chat → llm.py → llm_connect.generate_answer() → AI 서비스`이다.
외부 AI 키나 SDK를 프론트에서 사용하지 않는다.

## 현재 연결 상태

`llm.py`는 `Depends(get_current_user)`로 인증한 사용자의 질문만 통신 함수로 전달한다.
질문 앞뒤 공백을 제거하고 1~1,000자로 검증한다.
`generate_answer()`는 아직 `NotImplementedError`를 발생시키고, 라우터는 이를 HTTP 501로 변환한다.
실제 AI 호출·문맥 조회·대화 저장은 구현하지 않았다.

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
- 반환값: AI 답변 문자열. HTTP 응답 객체나 DB 모델을 반환하지 않는다.
- 현재 라우터는 빈 history를 전달한다. B가 DB 조회를 붙이면서 실제 기록으로 바꾼다.

## 구현 순서

1. 사용할 AI 제공자·모델을 정하고 필요한 SDK를 `uv add`로 추가한다.
2. `config.py`에 AI 키·모델·타임아웃 설정을 추가하고 `.env.example` 및 이 문서를 갱신한다.
   실제 키는 `.env` 또는 배포 환경변수에만 둔다. 기존 배포의 `--env-file` 주입을 사용한다.
3. `llm_connect.py`에서 비동기 API 호출을 구현한다. 타임아웃을 반드시 설정한다.
4. 이미 연결된 `get_current_user`와 `require_csrf_header`를 유지한다.
   라우터의 `user.id`를 DB 조회·저장의 사용자 기준으로 사용한다.
5. D의 모델로 해당 사용자의 최근 5쌍을 조회하고 통신 함수에 전달한다.
6. 답변을 받은 뒤 질문·답변을 저장하고 `{"answer":"..."}`를 반환한다.

통신 함수는 타임아웃·제공자 오류를 예외로 전달하고, `llm.py`에서 각각 504·502와
사용자용 `detail` 메시지로 바꾼다. 내부 응답이나 키를 오류 메시지에 그대로 노출하지 않는다.
POST 공통 헤더 누락·오류는 403, 인증 실패는 401, 인증 후 입력 검증 실패는 422로 처리한다.
DB 저장 실패는 rollback하고 성공 응답 대신 500과 저장 실패 안내를 반환한다.

요청 수신, AI 호출 시작, AI 응답·실패, DB 저장 성공·실패 이벤트를 logger로 기록한다.
사용자 식별·요청 추적에 필요한 값은 남기되 키·비밀번호·전체 요청 헤더는 기록하지 않는다.
AI를 기다리는 동안 DB 쓰기 트랜잭션을 열어두지 않는다.

## 작업 완료 확인

- 미로그인 상태에서 외부 AI가 호출되지 않는다.
- 이전 질문에 이어서 대화할 수 있고 다른 사용자의 문맥이 섞이지 않는다.
- 타임아웃·호출 실패·저장 실패에 오류 응답을 보내며 서버가 계속 동작한다.
- 성공한 질문·답변이 저장되고 D의 조회 API에서 확인된다.
- `feature/ai-chat`에서 작업하고 `develop` 대상으로 PR을 작성한다.
