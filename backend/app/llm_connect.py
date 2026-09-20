"""B 담당: 외부 AI 서비스와의 통신. 아직 실제 API를 호출하지 않는다.

구현 범위
- config.py에 AI 키·모델·타임아웃 환경변수 설정을 추가하고 통신에 사용한다.
- 실제 AI 요청, 타임아웃 제한, 응답 문자열 추출과 통신 오류 처리를 구현한다.
- AI 호출 시작·성공·실패·타임아웃 로그를 남긴다. 키와 질문·답변 본문은 기록하지 않는다.

llm.py와의 연결
- 인증·입력 검증·DB 문맥 조회·대화 저장은 llm.py에서 처리한다.
- 전달받은 history 뒤에 이번 question을 한 번 추가해 AI 요청을 구성한다.
- 성공하면 답변 문자열을 반환하고, 타임아웃·호출 실패는 구분 가능한 예외로 전달한다.
- HTTP 응답은 llm.py에서 만든다. B의 AI 연동 작업에 해당 예외를 504·502로 바꾸는
  llm.py 수정도 포함한다. 제공자의 오류 상세나 키를 사용자 응답에 노출하지 않는다.
"""


async def generate_answer(question: str, history: list[dict[str, str]]) -> str:
    """history는 오래된 순서의 role/content 메시지 목록, 반환값은 AI 답변 문자열."""
    raise NotImplementedError("AI 연결이 아직 구현되지 않았습니다.")
