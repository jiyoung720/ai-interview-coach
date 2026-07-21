"""Agent 분기 로직 회귀 테스트.

decide_next_step()은 State만 받는 순수 함수라 Gemini 호출 없이 검증할 수 있다.
CI 러너에는 API 키가 없으므로, 키가 필요 없는 이 계층을 회귀 테스트로 고정해둔다.
"""
import pytest

from rag.graph import build_chain_a_graph, build_interview_agent_graph
from rag.graph_nodes import ADVANCED_THRESHOLD, FUNDAMENTALS_THRESHOLD, decide_next_step
from rag.schemas import EvaluationResult


def make_state(technical_score: int) -> dict:
    return {
        "evaluation_result": EvaluationResult(
            technical_score=technical_score,
            completeness_score=5,
            strengths=[],
            improvements=[],
            overall_feedback="",
        )
    }


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (0, "fundamentals"), (1, "fundamentals"), (2, "fundamentals"), (3, "fundamentals"),
        (4, "learning_tip"), (5, "learning_tip"), (6, "learning_tip"),
        (7, "advanced"), (8, "advanced"), (9, "advanced"), (10, "advanced"),
    ],
)
def test_라우팅이_점수_전_구간에서_의도한_경로를_고른다(score, expected):
    assert decide_next_step(make_state(score)) == expected


def test_경계값이_상수와_일치한다():
    # 경계 바로 아래위에서 경로가 실제로 바뀌는지 확인.
    # 상수만 바꾸고 분기문을 고치지 않는 실수를 잡기 위함
    assert decide_next_step(make_state(FUNDAMENTALS_THRESHOLD - 1)) == "fundamentals"
    assert decide_next_step(make_state(FUNDAMENTALS_THRESHOLD)) == "learning_tip"
    assert decide_next_step(make_state(ADVANCED_THRESHOLD - 1)) == "learning_tip"
    assert decide_next_step(make_state(ADVANCED_THRESHOLD)) == "advanced"


def test_technical_score는_0에서_10_범위로_강제된다():
    # Judge가 범위 밖 점수를 반환하면 분기 기준 자체가 무너지므로 스키마에서 막는다
    with pytest.raises(ValueError):
        EvaluationResult(
            technical_score=11, completeness_score=5,
            strengths=[], improvements=[], overall_feedback="",
        )


def test_agent_그래프에_세_경로가_모두_연결되어_있다():
    graph = build_interview_agent_graph().get_graph()
    nodes = {n for n in graph.nodes if not n.startswith("__")}
    assert nodes == {"retrieval", "judge", "fundamentals", "learning_tip", "followup", "advanced"}

    # judge에서 세 갈래로 갈라지는지 확인
    targets = {e.target for e in graph.edges if e.source == "judge"}
    assert targets == {"fundamentals", "learning_tip", "advanced"}


def test_judge에서_END로_바로_가는_빈_경로가_없다():
    # v2에서는 점수가 높으면 아무 노드도 실행되지 않고 종료됐다.
    # v3에서 그 경로를 없앤 것이 되돌아가지 않도록 고정한다
    graph = build_interview_agent_graph().get_graph()
    judge_targets = {e.target for e in graph.edges if e.source == "judge"}
    assert "__end__" not in judge_targets


def test_learning_tip은_followup으로_이어진다():
    # 순차 설계(Learning Tip이 정한 topic을 Followup이 이어받음)가 유지되는지 확인
    graph = build_interview_agent_graph().get_graph()
    targets = {e.target for e in graph.edges if e.source == "learning_tip"}
    assert targets == {"followup"}


def test_chain_a는_검색후_생성으로_이어진다():
    graph = build_chain_a_graph().get_graph()
    nodes = {n for n in graph.nodes if not n.startswith("__")}
    assert nodes == {"retrieval", "generation"}
    assert {e.target for e in graph.edges if e.source == "retrieval"} == {"generation"}
