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
    # technical_score >= 5면 learning_tip/followup 노드가 아예 실행되지 않아
    # state에 해당 키가 없으므로 .get()으로 안전하게 조회 (없으면 None)
    learning_tip = result.get("learning_tip")

    return {
        **evaluation.model_dump(),
        "retrieved_sources": result["retrieved_sources"],
        "followup_question": result.get("followup_question"),
        "learning_tip": learning_tip.model_dump() if learning_tip else None,
    }
