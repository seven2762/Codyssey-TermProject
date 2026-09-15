"""B 담당: 외부 AI 서비스와의 통신. 아직 실제 API를 호출하지 않는다."""


async def generate_answer(question: str, history: list[dict[str, str]]) -> str:
    """history는 오래된 순서의 role/content 메시지 목록, 반환값은 AI 답변 문자열."""
    raise NotImplementedError("AI 연결이 아직 구현되지 않았습니다.")
