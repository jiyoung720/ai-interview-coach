from fastapi import APIRouter
from pydantic import BaseModel

from rag.graph import build_interview_agent_graph

router = APIRouter()


class EvaluateAnswerRequest(BaseModel):
    question: str
    answer: str


@router.post("/evaluate-answer")
def evaluate_answer(request: EvaluateAnswerRequest):
    graph = build_interview_agent_graph()
    result = graph.invoke({"question": request.question, "answer": request.answer})

    evaluation = result["evaluation_result"]
    return {
        **evaluation.model_dump(),
        "retrieved_sources": result["retrieved_sources"],
        "followup_question": result.get("followup_question"),
    }
