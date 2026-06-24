from fastapi import FastAPI

from api.documents import router as documents_router
from api.questions import router as questions_router

app = FastAPI(title="AI Interview Coach with RAG")
app.include_router(documents_router)
app.include_router(questions_router)


@app.get("/")
def health_check():
    return {"status": "ok"}
