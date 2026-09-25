"""백엔드 테스트 공통 설정. 실제 .env·DB·로그 대신 임시 디렉터리를 사용한다."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def application(tmp_path_factory):
    directory = tmp_path_factory.mktemp("backend")
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("DATABASE_PATH", str(directory / "test.db"))
        patch.setenv("SESSION_SECRET_KEY", "test-session-secret-not-for-deployment")
        patch.setenv("SESSION_MAX_AGE", "3600")
        patch.setenv("SESSION_HTTPS_ONLY", "false")
        # 테스트는 generate_answer를 대체하므로 실제 호출은 일어나지 않는다.
        patch.setenv("AI_API_KEY", "test-ai-key-not-for-deployment")
        patch.setenv("AI_BASE_URL", "https://ai.invalid/v1")
        patch.setenv("AI_MODEL", "test-model")
        patch.setenv("AI_TIMEOUT", "30")
        patch.chdir(directory)
        from app.main import app

        yield app


@pytest.fixture
def csrf_headers():
    return {"X-Requested-With": "XMLHttpRequest"}


@pytest.fixture
def client(application, csrf_headers):
    from app.db_connect import engine
    from app.models.chat import Chat
    from app.models.user import User

    with TestClient(application, headers=csrf_headers) as client:
        with engine.begin() as connection:
            connection.execute(Chat.__table__.delete())
            connection.execute(User.__table__.delete())
        yield client
