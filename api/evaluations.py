from fastapi import APIRouter
from pydantic import BaseModel

from rag.chains import get_chain_b

router = APIRouter()


class EvaluateAnswerRequest(BaseModel):
    question: str
    answer: str


@router.post("/evaluate-answer")
def evaluate_answer(request: EvaluateAnswerRequest):
    chain_b = get_chain_b()
    result = chain_b.invoke({"question": request.question, "answer": request.answer})
    return result
