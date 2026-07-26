# 문서의 실제 텍스트 처리(읽기, chunking)를 담당. documents.py가 이 함수들을 호출한다.
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


def load_text_file(file_path: str) -> str:
    return Path(file_path).read_text(encoding="utf-8")


def load_pdf_file(file_path: str) -> str:
    """PDF에서 텍스트만 추출한다.
    이 함수 하나가 "PDF 파싱 라이브러리"를 격리하는 경계다. 반환값이 순수 문자열이라,
    나중에 pdfplumber 등으로 바꿔도 이 함수 몸통만 고치면 되고 호출부는 바뀌지 않는다."""
    from pypdf import PdfReader

    reader = PdfReader(file_path)
    # 페이지별 추출 텍스트를 줄바꿈으로 이어붙임. 텍스트가 없는 페이지(스캔 이미지 등)는 ""를 반환
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def load_document(file_path: str) -> str:
    """확장자를 보고 적절한 로더로 분기한다. 텍스트 계열은 그대로 읽고, PDF만 별도 처리."""
    if Path(file_path).suffix.lower() == ".pdf":
        return load_pdf_file(file_path)
    return load_text_file(file_path)


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
