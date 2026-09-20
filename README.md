# AskMate - 로그인 기반 범용 AI 챗봇 프로젝트

로그인한 사용자가 AI와 대화하고 자신의 대화 기록을 조회하는 웹 서비스입니다.
현재는 Jinja2 화면 골격, 회원가입·로그인·세션 인증, SQLite 사용자·대화 테이블과 답변 수신 후 저장 처리가 구현되어 있습니다.
로그인 폼 등 화면 연동·실제 AI 호출·문맥 구성·대화 기록 조회는 아직 구현되지 않았습니다.

## 개발 환경

- Python 3.14.x (`backend/.python-version` 기준)
- [uv 설치](https://docs.astral.sh/uv/getting-started/installation/)
- FastAPI, Uvicorn (uv로 설치)

## 프로젝트 구조

```text
.
├── .github/                # Issue 및 PR 템플릿
├── docs/CONVENTIONS.md     # 협업 컨벤션
└── backend/
    ├── .python-version    # 개발에 사용할 Python 버전
    ├── pyproject.toml     # 프로젝트 설정과 의존성
    ├── uv.lock            # 하위 의존성을 포함한 버전 잠금 파일
    └── app/
        ├── __init__.py
        ├── main.py        # FastAPI 앱과 상태 확인 API
        ├── pages.py       # Jinja2 화면 경로
        ├── templates/     # 화면 HTML
        ├── static/        # CSS·JavaScript·이미지
        ├── account.py     # 회원가입·로그인·로그아웃·현재 사용자 API
        ├── account_db.py  # 사용자 저장·조회
        ├── chat_db.py     # 질문·답변 저장
        ├── auth.py        # 공통 세션 인증·POST 헤더 검사
        ├── security.py    # 비밀번호 해시·검증
        ├── models/        # 사용자·대화 기록 테이블
        ├── db_connect.py  # SQLite 연결·세션 제공
        └── llm_connect.py # 외부 AI 통신 위치 (현재 미구현)
```

## 설치와 실행

저장소를 clone한 뒤 저장소 루트에서 다음 명령을 실행합니다.

```bash
cd backend
uv sync
# 최초 실행 전에 아래 '환경 변수와 로컬 파일'의 비밀키 설정을 완료합니다.
uv run uvicorn app.main:app --reload
```

`uv sync`는 필요한 패키지를 `backend/.venv`에 설치합니다.
Python 3.14가 없으면 uv의 기본 설정에서는 필요한 Python도 자동으로 내려받습니다.
가상환경을 별도로 활성화할 필요 없이 `uv run`으로 실행할 수 있습니다.

- 서버 상태: <http://127.0.0.1:8000/health>
- API 문서: <http://127.0.0.1:8000/docs>
- 화면 골격: <http://127.0.0.1:8000/login> (`/signup`, `/chat`, `/history`도 제공)

`GET /health`의 정상 응답은 HTTP 200과 다음 JSON입니다.

```json
{"status": "ok"}
```

`/health`는 서버의 기본 응답 여부를 확인하며, DB나 외부 AI API의 연결 상태는 검사하지 않습니다.
`/` 경로는 `/login`으로 이동합니다. 서버 시작 시 SQLite 연결을 확인하고 사용자·대화 테이블을 준비합니다.
개발 서버는 `Ctrl+C`로 종료합니다. `--reload`는 개발용 옵션입니다.

애플리케이션 시작 메시지와 Uvicorn 접근·오류 로그는 콘솔과 실행 디렉터리의
`app.log`에 기록됩니다. 위 명령처럼 `backend/`에서 실행하면 `backend/app.log`가 생성됩니다.

## 의존성 관리

아래 명령도 `backend/`에서 실행합니다.

```bash
uv add <패키지명>
```

의존성을 변경하면 `pyproject.toml`과 `uv.lock`을 함께 커밋합니다.
팀원은 변경사항을 받은 뒤 `uv sync`를 실행합니다.
잠금 파일을 변경하지 않고 설치 상태를 검증하려면 `uv sync --locked`를 사용합니다.

## 환경 변수와 로컬 파일

`SESSION_SECRET_KEY`는 필수입니다. 최초 실행 시 `backend/.env.example`을 `.env`로 복사하고,
`uv run python -c "import secrets; print(secrets.token_urlsafe(32))"`로 생성한 값을 넣습니다.
기존 `.env`가 있다면 덮어쓰지 말고 설정만 추가합니다. 기본 세션 유효기간은 1시간이며,
HTTPS 배포에서는 `SESSION_HTTPS_ONLY=true`를 설정합니다.
`DATABASE_PATH`의 기본값은 `data/askmate.db`입니다.
상대 DB 경로는 `backend/` 기준이며, 배포 환경에서 전달한 값이 `.env`보다 우선합니다.
실제 `.env`, 가상환경, Python 캐시, 실행 중 생성되는 DB·로그 파일은 Git에서 제외합니다.
API 사용법과 세션 정책은 [계정·세션 인증 안내](docs/AUTH.md)를 참고하세요.

## 배포

GitHub Actions에서 Docker 이미지를 `2hynmin/codyssey-term`에 게시하고 Tailscale을
통해 OCI Compute 인스턴스에 배포합니다. OCI와 GitHub Secrets 준비, Tailnet 접근
정책, 로컬 Docker 검증, 배포 및 롤백 절차는
[OCI Docker 배포 가이드](docs/DEPLOYMENT.md)를 참고하세요.

## 협업

작업 브랜치는 최신 `develop`에서 생성하고, `작업 브랜치 → develop → main` 순서로
PR과 팀원 리뷰를 거쳐 병합합니다.
브랜치·커밋·리뷰·Issue 운영 기준은 [협업 컨벤션](docs/CONVENTIONS.md)을 참고하세요.

영역별 작업 방법은 [프론트](docs/FRONTEND.md), [DB·기록](docs/DATABASE.md),
[LLM](docs/LLM.md) 안내에 정리되어 있습니다.
