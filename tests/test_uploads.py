"""업로드 제한 (M0 S6, 로컬 모드 전용).

경로 조작 파일명, 크기 초과, 파싱 실패 시 인덱스를 건드리지 않는지 확인한다.
벡터 DB는 호출 여부만 기록하는 가짜로 바꿔 임베딩 모델 없이 돈다.
"""
import io

import pytest
from fastapi.testclient import TestClient

from core.uploads import UploadRejected, safe_display_name, save_upload


def test_경로_성분은_떼고_저장_파일명은_uuid다(tmp_path):
    assert safe_display_name("../../etc/evil.md") == "evil.md"
    assert safe_display_name("..\\..\\evil.md") == "evil.md"
    saved = save_upload(io.BytesIO(b"hello"), "../../evil.md", tmp_path / "uploads")
    assert saved.parent == tmp_path / "uploads"
    assert saved.name != "evil.md" and saved.suffix == ".md"


def test_크기를_넘으면_413이고_파일이_남지_않는다(tmp_path):
    with pytest.raises(UploadRejected) as rejected:
        save_upload(io.BytesIO(b"x" * 11), "a.txt", tmp_path, max_bytes=10)
    assert rejected.value.status_code == 413
    assert list(tmp_path.iterdir()) == []


def test_지원하지_않는_확장자는_400(tmp_path):
    with pytest.raises(UploadRejected) as rejected:
        save_upload(io.BytesIO(b"x"), "a.exe", tmp_path)
    assert rejected.value.status_code == 400


class FakeVectorstore:
    def __init__(self):
        self.calls = []

    def delete(self, **kwargs):
        self.calls.append(("delete", kwargs))

    def add_documents(self, docs):
        self.calls.append(("add", len(docs)))


@pytest.fixture
def documents_client(tmp_path, monkeypatch):
    from fastapi import FastAPI

    from api import documents

    fake = FakeVectorstore()
    monkeypatch.setattr(documents, "get_user_docs_vectorstore", lambda: fake)
    monkeypatch.setattr(documents, "UPLOAD_DIR", tmp_path / "uploads")
    app = FastAPI()
    app.include_router(documents.router)
    return TestClient(app), fake, tmp_path / "uploads"


def test_깨진_PDF는_422이고_인덱스를_건드리지_않는다(documents_client):
    client, fake, upload_dir = documents_client
    response = client.post("/documents", files={"file": ("resume.pdf", b"not a pdf", "application/pdf")})
    assert response.status_code == 422
    assert fake.calls == []                                   # 기존 인덱스는 그대로
    assert not upload_dir.exists() or list(upload_dir.iterdir()) == []


def test_정상_업로드는_원래_이름으로_교체_인덱싱한다(documents_client):
    client, fake, upload_dir = documents_client
    response = client.post("/documents", files={"file": ("../resume.md", "# 프로젝트\nRAG를 만들었다".encode(), "text/markdown")})
    assert response.status_code == 200
    assert response.json()["filename"] == "resume.md"
    assert fake.calls[0] == ("delete", {"where": {"source": "resume.md"}})
    assert fake.calls[1][0] == "add"
