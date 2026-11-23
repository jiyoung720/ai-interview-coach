"""세션 상태 전이표 (설계 §5.4). LLM 없는 순수 함수라 전수 테스트한다.

M0 골격의 상태: planning → awaiting_answer → done (계획 결과가 0개면 failed).
리포트 조립(reporting)은 M2에서 템플릿 리포트가 붙을 때 추가한다.
"""

ACTIONS = ("answer", "skip", "end")

# 상태별로 받을 수 있는 사용자 행동
ALLOWED_ACTIONS: dict[str, frozenset[str]] = {
    "planning": frozenset(),
    "awaiting_answer": frozenset(ACTIONS),
    "done": frozenset(),
    "failed": frozenset(),
}

# 턴을 처리한 결과 → 턴 기록의 event 값
OUTCOME_EVENTS = {
    "judged": "answered",            # 판정 성공 (unassessable 진단 포함)
    "judge_failed": "judge_failed",  # 최초 판정의 검증이 끝내 실패
    "skipped": "skipped",
    "ended": "ended",
}


def can_act(status: str, action: str) -> bool:
    return action in ALLOWED_ACTIONS.get(status, frozenset())


def status_after(outcome: str, next_question: dict | None) -> str:
    """턴을 처리한 뒤의 세션 상태. 종료이거나 다음 질문이 없으면 done."""
    if outcome == "ended" or next_question is None:
        return "done"
    return "awaiting_answer"


def status_after_plan(plan: list) -> str:
    return "awaiting_answer" if plan else "failed"
