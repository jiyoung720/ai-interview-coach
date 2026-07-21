"""Chunking 회귀 테스트.

Retrieval 품질이 chunk 경계에 좌우된다는 것을 실험으로 여러 번 확인했으므로
(제목만 담긴 chunk 문제, 비교형 문서 분리 역효과 등), chunking의 기본 동작을
회귀 테스트로 고정해둔다.
"""
from rag.loader import chunk_text


def test_chunk에_source_메타데이터가_붙는다():
    # source는 retrieved_sources 추출과 재업로드 시 삭제 기준으로 쓰이므로
    # 빠지면 조용히 기능이 깨진다
    docs = chunk_text("본문 " * 300, source="resume.md")
    assert docs
    assert all(d.metadata["source"] == "resume.md" for d in docs)


def test_짧은_문서는_하나의_chunk로_유지된다():
    docs = chunk_text("JWT는 토큰 기반 인증 방식이다.", source="jwt.md")
    assert len(docs) == 1


def test_긴_문서는_여러_chunk로_나뉜다():
    docs = chunk_text("가나다라마바사" * 500, source="long.md")
    assert len(docs) > 1


def test_chunk_size를_크게_벗어나지_않는다():
    # 분할기가 문단 경계를 존중하느라 다소 초과할 수 있으나,
    # 크게 벗어나면 여러 주제가 한 chunk에 섞여 유사도가 왜곡된다
    docs = chunk_text("문장입니다. " * 400, source="doc.md", chunk_size=500)
    assert all(len(d.page_content) <= 700 for d in docs)


def test_빈_문서는_chunk를_만들지_않는다():
    assert chunk_text("", source="empty.md") == []
