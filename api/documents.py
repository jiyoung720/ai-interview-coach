import shutil
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from rag.loader import chunk_text, load_text_file
from rag.vectorstore import get_user_docs_vectorstore

router = APIRouter()

UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

SUPPORTED_EXTENSIONS = {".md", ".txt"}


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
