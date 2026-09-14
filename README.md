# AskMate - 로그인 기반 범용 AI 챗봇 프로젝트

로그인한 사용자가 AI와 대화하고 자신의 대화 기록을 조회하는 웹 서비스입니다.
현재는 FastAPI 서버의 기본 실행 환경과 상태 확인 API까지 구현되어 있습니다.

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
        └── main.py        # FastAPI 앱과 상태 확인 API
```

## 설치와 실행

저장소를 clone한 뒤 저장소 루트에서 다음 명령을 실행합니다.

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload
```

`uv sync`는 필요한 패키지를 `backend/.venv`에 설치합니다.
Python 3.14가 없으면 uv의 기본 설정에서는 필요한 Python도 자동으로 내려받습니다.
가상환경을 별도로 활성화할 필요 없이 `uv run`으로 실행할 수 있습니다.

- 서버 상태: <http://127.0.0.1:8000/health>
- API 문서: <http://127.0.0.1:8000/docs>

`GET /health`의 정상 응답은 HTTP 200과 다음 JSON입니다.

```json
{"status": "ok"}
```

`/health`는 서버의 기본 응답 여부를 확인하며, DB나 외부 AI API의 연결 상태는 검사하지 않습니다.
현재 `/` 경로는 구현하지 않았으므로 위 주소로 확인합니다.
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

현재 서버 실행에 필요한 환경 변수는 없습니다.
인증·AI 연동에서 환경 변수를 도입할 때 `.env.example`과 설정 설명을 추가합니다.
실제 `.env`, 가상환경, Python 캐시, 실행 중 생성되는 DB·로그 파일은 Git에서 제외합니다.

## 협업

작업 브랜치는 최신 `develop`에서 생성하고, `작업 브랜치 → develop → main` 순서로
PR과 팀원 리뷰를 거쳐 병합합니다.
브랜치·커밋·리뷰·Issue 운영 기준은 [협업 컨벤션](docs/CONVENTIONS.md)을 참고하세요.
