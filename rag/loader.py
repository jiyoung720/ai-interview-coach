# 문서의 실제 텍스트 처리(읽기, chunking)를 담당. documents.py가 이 함수들을 호출한다.
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


def load_text_file(file_path: str) -> str:
    return Path(file_path).read_text(encoding="utf-8")


def chunk_text(
    text: str,
    source: str,
    chunk_size: int = 500,  # 너무 크면 여러 주제가 섞여 유사도가 왜곡되고, 너무 작으면
    chunk_overlap: int = 50,  # 제목만 남고 본문이 잘리는 chunk가 생길 수 있음 (실험 로그 참고)
) -> list[Document]:
    # 문단/문장 경계를 최대한 존중하며 자르는 분할기 (아무데서나 500자로 뚝 자르지 않음)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    chunks = splitter.split_text(text)
    # 각 조각을 Document(본문 + metadata)로 만듦. metadata의 source(파일명)는
    # 나중에 retrieved_sources 추출과 재업로드 시 chunk 삭제 기준으로 쓰인다.
    return [
        Document(page_content=chunk, metadata={"source": source})
        for chunk in chunks
    ]
