# POST /documents 엔드포인트를 담당하는 파일
# 역할: 사용자가 올린 문서를 받아서, 검색 가능한 상태(벡터 DB)로 만들어두는 것
import shutil
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from rag.loader import chunk_text, load_text_file
from rag.vectorstore import get_user_docs_vectorstore

router = APIRouter()

# 업로드 된 파일을 저장할 디렉토리 생성
UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)   # 이미 있으면 그냥 넘어가고, 없으면 생성

SUPPORTED_EXTENSIONS = {".md", ".txt"}

# 문서 업로드 (Chain A가 나중에 검색할 데이터를 미리 인덱싱해두는 사전 준비 단계. Chain A 자체는 questions.py)
# 처리 흐름: 파일 저장 -> 텍스트 읽기 -> 500자 chunking -> 기존 chunk 삭제 -> 임베딩+저장
@router.post("/documents")
def upload_document(file: UploadFile = File(...)):
    suffix = Path(file.filename).suffix.lower()
    # 형식 검사: 지원하지 않는 형식이면 400 에러 반환
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 형식입니다: {suffix} (현재는 .md, .txt만 지원)",
        )
    # 파일 저장: 로드 스트림을 data/uploads/파일명으로 디스크에 복사
    save_path = UPLOAD_DIR / file.filename
    with save_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    # 텍스트 읽기 및 chunking (rag/loader.py를 호출)
    text = load_text_file(str(save_path))
    documents = chunk_text(text, source=file.filename)

    # 벡터 DB에 chunk 저장 (rag/vectorstore.py를 호출)
    vectorstore = get_user_docs_vectorstore()

    # 같은 파일명으로 재업로드되면 예전 chunk를 먼저 지움 (중복 누적 방지)
    vectorstore.delete(where={"source": file.filename})

    # 인덱싱: add_documents 이 한 줄 안에서 Chroma가 각 chunk를 임베딩(벡터 변환)해 저장함
    # (코드에 "embed"라는 말이 안 보여도 임베딩이 일어나는 지점)
    vectorstore.add_documents(documents)

    # 반환: 업로드된 파일명과 chunk 개수
    return {"filename": file.filename, "chunks_added": len(documents)}
