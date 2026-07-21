# 그래프가 노드 사이로 들고 다니는 State의 정의서
# 노드가 state["..."]로 읽고 return {"...": ...}로 채우는 모든 키가 여기 모여 있다.
from typing import TypedDict

from rag.schemas import EvaluationResult, InterviewQuestions, LearningTip


class InterviewState(TypedDict, total=False):
    """Chain A/B를 LangGraph StateGraph로 마이그레이션하기 위한 State.

    total=False로 선언해 필드를 단계적으로 채워나갈 수 있게 함.
    (기본값 total=True면 시작 시 모든 키를 채워야 해서 이 그래프 구조가 성립하지 않음)"""

    # 공통 입력 (graph.invoke에 넣는 값. question은 Chain A/B 둘 다, answer는 Chain B만)
    question: str
    answer: str

    # Retrieval Node가 채움 (Chain A/B 공통)
    context: str                    # 검색된 chunk 본문을 이어붙인 문자열
    retrieved_sources: list[str]    # 검색된 출처 파일명 목록

    # Chain A: Generation Node가 채움
    generated_questions: InterviewQuestions

    # Chain B: Judge Node가 채움
    evaluation_result: EvaluationResult

    # Agent 확장: technical_score < 5일 때만 채워짐 (병렬이 아니라 learning_tip -> followup 순차 실행)
    # 이 키들은 없을 수 있어서, api에서 result.get(...)으로 안전하게 꺼냄
    next_action: str
    followup_question: str
    learning_tip: LearningTip
