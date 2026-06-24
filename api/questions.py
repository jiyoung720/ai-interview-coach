from fastapi import APIRouter
from pydantic import BaseModel

from rag.chains import get_chain_a

router = APIRouter()


class GenerateQuestionRequest(BaseModel):
    query: str = "프로젝트 기술 스택"


@router.post("/generate-question")
def generate_question(request: GenerateQuestionRequest):
    chain_a = get_chain_a()
    result = chain_a.invoke(request.query)
    return {"questions": result.questions}
