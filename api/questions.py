from fastapi import APIRouter
from pydantic import BaseModel

from rag.graph import build_chain_a_graph

router = APIRouter()


class GenerateQuestionRequest(BaseModel):
    query: str = "프로젝트 기술 스택"

# 질문 생성 요청
@router.post("/generate-question")
def generate_question(request: GenerateQuestionRequest):
    graph = build_chain_a_graph()   # 그래프 만들고,
    result = graph.invoke({"question": request.query})  # 그래프 호출
    return {"questions": result["generated_questions"].questions}
