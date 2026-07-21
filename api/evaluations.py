# POST /evaluate-answer 엔드포인트 담당
# 역할: 사용자가 답변한 내용을 받아서, 그 답변이 적절한지 채점하고 → 점수 구간에 맞는 코칭을 붙여 → 하나의 JSON으로 돌려줌
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
    # Agent 분기가 포함된 그래프
    # (구조: START → retrieval → judge → [점수 구간별 3분기] → END)
    graph = build_interview_agent_graph()
    result = graph.invoke({"question": request.question, "answer": request.answer})

    # 결과 꺼내기
    evaluation = result["evaluation_result"]
    # 점수 구간에 따라 셋 중 한 경로만 실행되므로, 나머지 키는 state에 아예 없다.
    # 그래서 .get()으로 안전하게 조회 (없으면 None)
    learning_tip = result.get("learning_tip")
    concept_explanation = result.get("concept_explanation")
    advanced_question = result.get("advanced_question")

    # 최종 JSON 조립
    return {
        **evaluation.model_dump(),  # EvaluationResult 객체를 dict로 펼치기
        "retrieved_sources": result["retrieved_sources"],   # 어느 KB 문서에서 검색됐는지 (이건 retrieval_node가 항상 채우니까 [...]로 꺼낸다)
        "next_action": result.get("next_action"),   # 어느 경로가 실행됐는지 (분기 확인용)
        # 0~3점 경로
        "concept_explanation": concept_explanation.model_dump() if concept_explanation else None,
        # 4~6점 경로
        "learning_tip": learning_tip.model_dump() if learning_tip else None,
        "followup_question": result.get("followup_question"),
        # 7~10점 경로
        "advanced_question": advanced_question.model_dump() if advanced_question else None,
    }
