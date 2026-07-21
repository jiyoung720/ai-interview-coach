# POST /evaluate-answer 엔드포인트 담당
# 역할: 사용자가 답변한 내용을 받아서, 그 답변이 적절한지 채점하고 → 점수가 낮으면 학습 팁과 꼬리질문까지 만들어 → 하나의 JSON으로 돌려줌
# Chain B + Agent 진입점
from fastapi import APIRouter
from pydantic import BaseModel

from rag.graph import build_interview_agent_graph

router = APIRouter()


class EvaluateAnswerRequest(BaseModel):
    question: str   # 면접 질문
    answer: str     # 사용자 답변


@router.post("/evaluate-answer")
def evaluate_answer(request: EvaluateAnswerRequest):
    # Agent 분기가 포함된 그래프 (구조: START → retrieval → judge → [조건부 분기] → (learning_tip → followup) → END)
    graph = build_interview_agent_graph()
    result = graph.invoke({"question": request.question, "answer": request.answer})

    # 결과 꺼내기
    evaluation = result["evaluation_result"]
    # technical_score >= 5면 learning_tip/followup 노드가 아예 실행되지 않아
    # state에 해당 키가 없으므로 .get()으로 안전하게 조회 (없으면 None)
    learning_tip = result.get("learning_tip")

    # 최종 JSON 조립
    return {
        **evaluation.model_dump(),  # EvaluationResult 객체를 dict로 펼치기
        "retrieved_sources": result["retrieved_sources"],   # 어느 KB 문서에서 검색됐는지 (이건 retrieval_node가 항상 채우니까 [...]로 꺼낸다)
        "followup_question": result.get("followup_question"),   # 꼬리질문
        "learning_tip": learning_tip.model_dump() if learning_tip else None,
    }
