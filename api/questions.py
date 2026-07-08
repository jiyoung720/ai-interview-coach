from fastapi import APIRouter
from pydantic import BaseModel

from rag.graph import build_chain_a_graph

router = APIRouter()


class GenerateQuestionRequest(BaseModel):
    query: str = "프로젝트 기술 스택"


@router.post("/generate-question")
def generate_question(request: GenerateQuestionRequest):
    graph = build_chain_a_graph()
    result = graph.invoke({"question": request.query})
    return {"questions": result["generated_questions"].questions}
