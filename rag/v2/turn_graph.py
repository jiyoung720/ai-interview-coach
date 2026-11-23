"""v2 면접 엔진의 골격 (M0).

v2는 LangGraph 체크포인터와 interrupt를 쓰지 않는다. 세션 상태는 SQLite(core/)가 들고,
요청 하나마다 이 그래프를 **한 턴만** 실행한다 (설계 §5.4, §7.1).

    load(SQLite) → [judge → decide] → commit(SQLite)

M0에서는 판정 노드가 가짜다. 진짜 판정·근거 보강·코칭은 M1~M2에서 judge 자리에 들어간다.
여기서 검증하려는 것은 LLM 품질이 아니라, 턴 단위 실행과 SQLite 단일 저장소의 계약이다.
"""
from typing import Callable, Protocol, TypedDict

from langgraph.graph import END, START, StateGraph

MAX_FOLLOWUPS = 1   # MVP: 메인 질문당 꼬리질문 최대 1개 (설계 §5.1)


class TurnEngine(Protocol):
    def plan(self, request: dict) -> list[dict]: ...
    def run_turn(self, state: dict, answer: str) -> dict: ...


class TurnState(TypedDict, total=False):
    plan: list[dict]
    cursor: dict              # {"main_index": int, "depth": int}
    question: dict            # 지금 답한 질문
    answer: str
    judgement: dict           # 판정 결과 (M0: 가짜)
    next_question: dict | None
    next_cursor: dict


def fake_judge(question: dict, answer: str) -> dict:
    """M0용 가짜 판정. 답변에 '모름'이 있으면 partial로 보고 꼬리질문을 유도한다."""
    diagnosis = "partial" if "모름" in answer else "solid"
    return {"diagnosis": diagnosis}


def decide_next(plan: list[dict], cursor: dict, question: dict, diagnosis: str) -> tuple[dict | None, dict]:
    """다음에 물을 질문과 커서를 고른다. LLM 없는 순수 함수."""
    main_index, depth = cursor["main_index"], cursor["depth"]
    if diagnosis == "partial" and depth < MAX_FOLLOWUPS:
        parent_id = question.get("parent_id") or question["id"]
        followup = {
            "id": f"{parent_id}-f{depth + 1}",
            "text": f"[꼬리질문] {question['text']}",
            "depth": depth + 1,
            "parent_id": parent_id,
        }
        return followup, {"main_index": main_index, "depth": depth + 1}

    next_index = main_index + 1
    if next_index >= len(plan):
        return None, {"main_index": next_index, "depth": 0}
    return plan[next_index], {"main_index": next_index, "depth": 0}


class SkeletonEngine:
    """가짜 계획 + 가짜 판정으로 도는 엔진. 테스트는 judge·planner를 바꿔 끼운다."""

    def __init__(self, judge: Callable[[dict, str], dict] = fake_judge, planner: Callable[[dict], list[dict]] | None = None):
        self.judge = judge
        self.planner = planner or self._default_plan
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

        def decide_node(state: TurnState) -> dict:
            nxt, cursor = decide_next(state["plan"], state["cursor"], state["question"], state["judgement"]["diagnosis"])
            return {"next_question": nxt, "next_cursor": cursor}

        graph = StateGraph(TurnState)
        graph.add_node("judge", judge_node)
        graph.add_node("decide", decide_node)
        graph.add_edge(START, "judge")
        graph.add_edge("judge", "decide")
        graph.add_edge("decide", END)
        return graph.compile()   # 체크포인터 없음: 상태는 호출자가 SQLite에서 넣고 받아 간다

    def run_turn(self, state: dict, answer: str) -> dict:
        result = self._graph.invoke({**state, "answer": answer})
        return {
            "judgement": result["judgement"],
            "next_question": result["next_question"],
            "next_cursor": result["next_cursor"],
        }
