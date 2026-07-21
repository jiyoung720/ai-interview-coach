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
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    chunks = splitter.split_text(text)
    return [
        Document(page_content=chunk, metadata={"source": source})
        for chunk in chunks
    ]
