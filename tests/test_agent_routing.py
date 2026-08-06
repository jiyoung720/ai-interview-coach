"""Agent 분기 로직 회귀 테스트.

decide_next_step()은 State만 받는 순수 함수라 Gemini 호출 없이 검증할 수 있다.
CI 러너에는 API 키가 없으므로, 키가 필요 없는 이 계층을 회귀 테스트로 고정해둔다.
"""
import pytest

from rag.config import SCOPE_DISTANCE_THRESHOLD
from rag.graph import build_chain_a_graph, build_interview_agent_graph
from rag.graph_nodes import (
    ADVANCED_THRESHOLD,
    FUNDAMENTALS_THRESHOLD,
    decide_next_step,
    decide_scope,
    out_of_scope_node,
)
from rag.schemas import AdvancedQuestion, EvaluationResult, LearningTip


def make_state(technical_score: int) -> dict:
    return {
        "evaluation_result": EvaluationResult(
            deductions=[],
            technical_score=technical_score,
            completeness_score=5,
            level="middle",
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
            deductions=[], technical_score=11, completeness_score=5, level="middle",
            strengths=[], improvements=[], overall_feedback="",
        )


def test_level은_정해진_세_값만_허용된다():
    # 자유 문자열로 두면 Judge가 "주니어", "Junior", "entry" 등 제각각 반환해
    # 화면에서 분기 처리를 할 수 없다
    with pytest.raises(ValueError):
        EvaluationResult(
            deductions=[], technical_score=5, completeness_score=5, level="주니어",
            strengths=[], improvements=[], overall_feedback="",
        )


def test_agent_그래프에_세_경로가_모두_연결되어_있다():
    graph = build_interview_agent_graph().get_graph()
    nodes = {n for n in graph.nodes if not n.startswith("__")}
    assert nodes == {
        "retrieval", "judge", "fundamentals", "learning_tip", "followup", "advanced", "out_of_scope",
    }

    # judge에서 세 갈래로 갈라지는지 확인
    targets = {e.target for e in graph.edges if e.source == "judge"}
    assert targets == {"fundamentals", "learning_tip", "advanced"}


def test_근거가_멀면_judge를_거치지_않는다():
    # 검색은 근거가 없어도 항상 상위 3개를 돌려주므로, 거리로 걸러내지 않으면
    # 엉뚱한 문서를 근거로 점수가 매겨진다 (Phase 17)
    graph = build_interview_agent_graph().get_graph()
    targets = {e.target for e in graph.edges if e.source == "retrieval"}
    assert targets == {"judge", "out_of_scope"}


@pytest.mark.parametrize(
    "distance, expected",
    [
        (SCOPE_DISTANCE_THRESHOLD - 0.001, "in_scope"),
        (SCOPE_DISTANCE_THRESHOLD, "out_of_scope"),        # 경계값은 범위 밖으로 본다
        (SCOPE_DISTANCE_THRESHOLD + 0.001, "out_of_scope"),
    ],
)
def test_범위_판정은_임계값을_경계로_갈린다(distance, expected):
    assert decide_scope({"out_of_scope": distance >= SCOPE_DISTANCE_THRESHOLD}) == expected


def test_범위_밖_노드는_점수를_만들지_않는다():
    # 틀린 근거로 매긴 점수를 사용자가 자기 실력으로 받아들이면 오히려 해롭다
    result = out_of_scope_node({"question": "Kafka 리밸런싱은?", "answer": "..."})
    assert "evaluation_result" not in result
    assert "learning_tip" not in result
    assert result["next_action"] == "out_of_scope"


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


def test_이전_턴의_코칭이_이번_턴_결과로_새지_않는다():
    # LangGraph State는 턴을 넘어 누적된다. 1턴이 learning_tip 경로였고 2턴이
    # advanced 경로였다면, 2턴 State에도 1턴의 learning_tip이 그대로 남아 있다.
    # next_action으로 이번 턴에 실제로 돈 경로만 골라내지 않으면 코칭이 두 개 나간다.
    from api.interviews import _coaching_payload

    values = {
        "next_action": "advanced_question_generated",
        "learning_tip": LearningTip(topic="세션", reason="...", recommended_sections=[]),
        "followup_question": "1턴에서 만든 꼬리질문",
        "advanced_question": AdvancedQuestion(question="2턴 심화 질문", intent="..."),
    }
    payload = _coaching_payload(values)

    assert payload["advanced_question"]["question"] == "2턴 심화 질문"
    assert payload["learning_tip"] is None
    assert payload["followup_question"] is None


def test_범위_밖_턴에는_코칭을_내보내지_않는다():
    from api.interviews import _coaching_payload

    values = {
        "next_action": "out_of_scope",
        "learning_tip": LearningTip(topic="직전 턴", reason="...", recommended_sections=[]),
    }
    assert _coaching_payload(values, out_of_scope=True)["learning_tip"] is None
