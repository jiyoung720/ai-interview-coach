# POST /documents (v1, 로컬 모드 전용)
# 역할: 사용자가 올린 문서를 받아서, 검색 가능한 상태(벡터 DB)로 만들어두는 것
#
# 저장·검증은 core/uploads.py가 맡는다: uuid 저장 파일명, 크기·페이지 수·파싱 시간 상한.
# 파싱이 끝나 텍스트가 확보된 뒤에만 인덱스를 건드린다. 그 전에 실패하면 기존 인덱스는 그대로다.
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from core.uploads import UploadRejected, check_pdf_pages, parse_with_timeout, safe_display_name, save_upload
from rag.loader import chunk_text, load_document
from rag.vectorstore import get_user_docs_vectorstore

router = APIRouter()

UPLOAD_DIR = Path("data/uploads")


@router.post("/documents")
def upload_document(file: UploadFile = File(...)):
    display_name = safe_display_name(file.filename)
    try:
        save_path = save_upload(file.file, file.filename, UPLOAD_DIR)
    except UploadRejected as rejected:
        raise HTTPException(status_code=rejected.status_code, detail=rejected.detail) from rejected

    try:
        check_pdf_pages(save_path)
        text = parse_with_timeout(load_document, save_path)
    except UploadRejected as rejected:
        save_path.unlink(missing_ok=True)
        raise HTTPException(status_code=rejected.status_code, detail=rejected.detail) from rejected

    # source는 v1 동작대로 원래 파일명(경로 성분 제거). 같은 이름 재업로드 시 예전 chunk를 교체한다
    documents = chunk_text(text, source=display_name)
    if not documents:
        save_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=422,
            detail="파일에서 추출된 텍스트가 없습니다 (스캔 이미지 PDF일 수 있습니다).",
        )

    vectorstore = get_user_docs_vectorstore()
    vectorstore.delete(where={"source": display_name})
    vectorstore.add_documents(documents)

    return {"filename": display_name, "chunks_added": len(documents)}
