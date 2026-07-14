import shutil
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from rag.loader import chunk_text, load_text_file
from rag.vectorstore import get_user_docs_vectorstore

router = APIRouter()

UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

SUPPORTED_EXTENSIONS = {".md", ".txt"}

# 질문 생성 (Chain A)
# 입력: multipart 파일
# 처리: 파일을 data/uploads/에 저장 → load_text_file()로 텍스트 읽기(rag/loader.py:7-8) 
# → chunk_text()로 500자 단위(overlap 50자)로 분할 (rag/loader.py:11-25), 각 chunk에 metadata={"source": 파일명} 부착 
# → 같은 파일명으로 재업로드되면 기존 chunk를 먼저 삭제
@router.post("/documents")
def upload_document(file: UploadFile = File(...)):
    suffix = Path(file.filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 형식입니다: {suffix} (현재는 .md, .txt만 지원)",
        )

    save_path = UPLOAD_DIR / file.filename
    with save_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    text = load_text_file(str(save_path))
    documents = chunk_text(text, source=file.filename)

    vectorstore = get_user_docs_vectorstore()

    # 같은 파일명으로 재업로드되면 예전 chunk를 먼저 지움 (중복 누적 방지)
    vectorstore.delete(where={"source": file.filename})

    vectorstore.add_documents(documents)

    return {"filename": file.filename, "chunks_added": len(documents)}
