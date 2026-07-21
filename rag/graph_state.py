from typing import TypedDict

from rag.schemas import EvaluationResult, InterviewQuestions, LearningTip


class InterviewState(TypedDict, total=False):
    """Chain A/B를 LangGraph StateGraph로 마이그레이션하기 위한 State.

    total=False로 선언해 필드를 단계적으로 채워나갈 수 있게 함."""

    # 공통 입력
    question: str
    answer: str

    # Retrieval Node가 채움 (Chain A/B 공통)
    context: str
    retrieved_sources: list[str]

    # Chain A: Generation Node가 채움
    generated_questions: InterviewQuestions

    # Chain B: Judge Node가 채움
    evaluation_result: EvaluationResult

    # Agent 확장: technical_score < 5일 때만 채워짐 (병렬이 아니라 learning_tip -> followup 순차 실행)
    next_action: str
    followup_question: str
    learning_tip: LearningTip
