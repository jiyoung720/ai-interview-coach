"""배포 경계 회귀 테스트 (M0 S1).

공개 서버(demo)에 v1 엔드포인트와 업로드가 열리지 않는지, 설정을 빠뜨렸을 때
안전한 쪽(demo)으로 기동하는지를 API 키 없이 확인한다.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from core.config import ConfigError, load_settings

V1_PATHS = [
    ("post", "/documents"),
    ("post", "/generate-question"),
    ("post", "/evaluate-answer"),
    ("post", "/interview/start"),
    ("post", "/interview/answer"),
]


def test_APP_MODE가_없으면_데모_모드로_기동하고_v1_경로가_없다(tmp_path):
    # 테스트용 비밀키만 주고 APP_MODE와 Gemini 키는 주지 않는다
    settings = load_settings({"SECRET_KEY": "test-secret", "DATA_DIR": str(tmp_path)})
    assert settings.is_demo

    with TestClient(create_app(settings)) as client:
        assert client.get("/health").json() == {"status": "ok", "mode": "demo"}
        for method, path in V1_PATHS:
            assert getattr(client, method)(path).status_code == 404, path
        # 기동 시 앱 DB가 만들어진다
        assert settings.db_path.exists()


def test_데모_모드에_SECRET_KEY가_없으면_기동하지_않는다(tmp_path):
    with pytest.raises(ConfigError):
        load_settings({"APP_MODE": "demo", "DATA_DIR": str(tmp_path)})


def test_알_수_없는_모드는_거부한다(tmp_path):
    with pytest.raises(ConfigError):
        load_settings({"APP_MODE": "prod", "SECRET_KEY": "x", "DATA_DIR": str(tmp_path)})


def test_로컬_모드는_v1_라우터를_등록한다(tmp_path):
    settings = load_settings({"APP_MODE": "local", "DATA_DIR": str(tmp_path)})
    paths = set(create_app(settings).openapi()["paths"])
    assert {"/documents", "/generate-question", "/evaluate-answer", "/interview/start"} <= paths
