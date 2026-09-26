# syntax=docker/dockerfile:1

FROM ghcr.io/astral-sh/uv:0.12.13-python3.14-trixie-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project

COPY app ./app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

RUN useradd --create-home --uid 10001 askmate \
    && mkdir -p /app/data \
    && chown -R askmate:askmate /app

USER askmate

EXPOSE 8000

# B 담당 배포 검증: 프로세스 실행 여부가 아니라 실제 HTTP 응답을 확인한다.
# 이 상태가 healthy가 되어야 워크플로가 이전 컨테이너를 제거한다.
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=5 \
    CMD [".venv/bin/python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"]

CMD [".venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
