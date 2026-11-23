"""v2 면접 엔진의 골격 (M0).

v2는 LangGraph 체크포인터와 interrupt를 쓰지 않는다. 세션 상태는 SQLite(core/)가 들고,
요청 하나마다 이 그래프를 **한 턴만** 실행한다 (설계 §5.4, §7.1).

    load(SQLite) → [judge → coach → decide] → commit(SQLite)

M0에서는 판정·코칭 노드가 가짜다. 진짜 판정·근거 보강·코칭은 M1~M2에서 이 자리에 들어간다.
여기서 검증하려는 것은 LLM 품질이 아니라, 턴 단위 실행과 SQLite 단일 저장소의 계약이다.
"""
from typing import Callable, Protocol, TypedDict

from langgraph.graph import END, START, StateGraph

from core.budget import BudgetExhausted

MAX_FOLLOWUPS = 1   # MVP: 메인 질문당 꼬리질문 최대 1개 (설계 §5.1)


class JudgeFailed(Exception):
    """최초 판정의 검증이 재판정 후에도 실패했다. 턴을 judge_failed로 기록하고 다음 메인으로 간다."""


class TurnEngine(Protocol):
    def plan(self, request: dict) -> list[dict]: ...
    def run_turn(self, state: dict, answer: str) -> dict: ...
    def skip(self, state: dict) -> dict: ...


class TurnState(TypedDict, total=False):
    plan: list[dict]
    cursor: dict              # {"main_index": int, "depth": int}
    question: dict            # 지금 답한 질문
    answer: str
    judgement: dict
    coaching: dict | None
    coaching_skipped: bool    # 판정 후 예산 소진으로 코칭·꼬리질문을 생략했는가
    next_question: dict | None
    next_cursor: dict


def fake_judge(question: dict, answer: str) -> dict:
    """M0용 가짜 판정. 답변에 '모름'이 있으면 partial로 보고 꼬리질문을 유도한다."""
    diagnosis = "partial" if "모름" in answer else "solid"
    return {"diagnosis": diagnosis}


def next_main(plan: list[dict], cursor: dict) -> tuple[dict | None, dict]:
    next_index = cursor["main_index"] + 1
    question = plan[next_index] if next_index < len(plan) else None
    return question, {"main_index": next_index, "depth": 0}


def decide_next(plan: list[dict], cursor: dict, question: dict, diagnosis: str) -> tuple[dict | None, dict]:
    """다음에 물을 질문과 커서를 고른다. LLM 없는 순수 함수."""
    depth = cursor["depth"]
    if diagnosis == "partial" and depth < MAX_FOLLOWUPS:
        parent_id = question.get("parent_id") or question["id"]
        followup = {
            "id": f"{parent_id}-f{depth + 1}",
            "text": f"[꼬리질문] {question['text']}",
            "depth": depth + 1,
            "parent_id": parent_id,
        }
        return followup, {"main_index": cursor["main_index"], "depth": depth + 1}
    return next_main(plan, cursor)


class SkeletonEngine:
    """가짜 계획 + 가짜 판정으로 도는 엔진. 테스트는 judge·coach·planner를 바꿔 끼운다."""

    def __init__(self, judge: Callable[[dict, str], dict] = fake_judge,
                 planner: Callable[[dict], list[dict]] | None = None,
                 coach: Callable[[dict, dict], dict] | None = None):
        self.judge = judge
        self.planner = planner or self._default_plan
        self.coach = coach
        self._graph = self._build()

    @staticmethod
    def _default_plan(request: dict) -> list[dict]:
        return [
            {"id": "q1", "text": "가짜 질문 1", "depth": 0},
            {"id": "q2", "text": "가짜 질문 2", "depth": 0},
        ]

    def plan(self, request: dict) -> list[dict]:
        return self.planner(request)

    def _build(self):
        def judge_node(state: TurnState) -> dict:
            return {"judgement": self.judge(state["question"], state["answer"])}

        def coach_node(state: TurnState) -> dict:
            if self.coach is None:
                return {"coaching": None, "coaching_skipped": False}
            try:
                return {"coaching": self.coach(state["question"], state["judgement"]), "coaching_skipped": False}
            except BudgetExhausted:
                # 판정 후 예산 소진: 판정은 보존하고 코칭·꼬리질문은 생략한다 (설계 §2.5)
                return {"coaching": None, "coaching_skipped": True}

        def decide_node(state: TurnState) -> dict:
            if state["coaching_skipped"]:
                nxt, cursor = next_main(state["plan"], state["cursor"])
            else:
                nxt, cursor = decide_next(state["plan"], state["cursor"], state["question"],
                                          state["judgement"]["diagnosis"])
            return {"next_question": nxt, "next_cursor": cursor}

        graph = StateGraph(TurnState)
        graph.add_node("judge", judge_node)
        graph.add_node("coach", coach_node)
        graph.add_node("decide", decide_node)
        graph.add_edge(START, "judge")
        graph.add_edge("judge", "coach")
        graph.add_edge("coach", "decide")
        graph.add_edge("decide", END)
        return graph.compile()   # 체크포인터 없음: 상태는 호출자가 SQLite에서 넣고 받아 간다

    def run_turn(self, state: dict, answer: str) -> dict:
        try:
            result = self._graph.invoke({**state, "answer": answer})
        except JudgeFailed:
            nxt, cursor = next_main(state["plan"], state["cursor"])
            return {"outcome": "judge_failed", "judgement": None, "coaching": None,
                    "coaching_skipped": False, "next_question": nxt, "next_cursor": cursor}
        return {
            "outcome": "judged",
            "judgement": result["judgement"],
            "coaching": result["coaching"],
            "coaching_skipped": result["coaching_skipped"],
            "next_question": result["next_question"],
            "next_cursor": result["next_cursor"],
        }

    def skip(self, state: dict) -> dict:
        nxt, cursor = next_main(state["plan"], state["cursor"])
        return {"outcome": "skipped", "next_question": nxt, "next_cursor": cursor}
