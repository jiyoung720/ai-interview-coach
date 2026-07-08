from typing import TypedDict

from rag.schemas import EvaluationResult, InterviewQuestions


class InterviewState(TypedDict, total=False):
    """Chain A/B를 LangGraph StateGraph로 마이그레이션하기 위한 State.

    total=False로 선언해 필드를 단계적으로 채워나갈 수 있게 함."""

    # 공통 입력
    question: str  # Chain B(답변 평가) 입력, Chain A 검색 쿼리로도 사용
    answer: str     # Chain B 전용

    # Retrieval Node가 채움 (Chain A/B 공통)
    context: str
    retrieved_sources: list[str]

    # Chain A: Generation Node가 채움
    generated_questions: InterviewQuestions

    # Chain B: Judge Node가 채움
    evaluation_result: EvaluationResult

    # 아직 사용하지 않음 — 추후 Agent 확장(점수 기반 분기) 대비
    next_action: str
    followup_question: str
