from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.documents import router as documents_router
from api.evaluations import router as evaluations_router
from api.questions import router as questions_router

# FastAPI 앱이 라우터 3개를 붙임
app = FastAPI(title="AI Interview Coach with RAG")
app.include_router(documents_router)
app.include_router(questions_router)
app.include_router(evaluations_router)

# 프론트엔드 정적 파일(css/js)을 /static 경로로 서빙.
# 프론트를 별도 서버가 아니라 이 FastAPI가 직접 서빙하므로 CORS 문제가 없다.
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/")
def index():
    # 루트로 접속하면 데모 페이지를 보여준다
    return FileResponse(STATIC_DIR / "index.html")
