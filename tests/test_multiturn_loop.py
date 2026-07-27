"""멀티턴 루프(Phase 11)의 사이클 동작 회귀 테스트.

노드 내부의 Gemini 호출을 가짜 노드로 갈아끼워, **루프 메커니즘만** 검증한다.
그래서 API 키 없이 CI에서 그대로 돌릴 수 있다.
(CI test job이 "키가 필요 없는 계층만 검증"하도록 설계된 것과 같은 이유)

여기서 확인하려는 것은 LLM의 출력 품질이 아니라 다음 네 가지다.
1. interrupt로 멈췄다가 resume으로 재개되는가
2. 재개 후 실제로 retrieval/judge로 되돌아가는가 (= 사이클이 도는가)
3. MAX_TURNS에서 멈추는가
4. 턴이 넘어갈 때 질문이 교체되고 이전 턴이 history에 쌓이는가
"""
import pytest
from langgraph.types import Command

from rag import graph as graph_module
from rag.graph_nodes import MAX_TURNS
from rag.schemas import (
    AdvancedQuestion,
    ConceptExplanation,
    EvaluationResult,
    LearningTip,
)


def _patch_nodes(monkeypatch, judge_scores):
    """모든 LLM 노드를 가짜로 교체하고, judge 호출 횟수를 세는 카운터를 돌려준다.

    judge_scores는 턴 순서대로 낼 technical_score 목록이다.
    (예: [5, 5, 5]이면 세 턴 모두 4~6점 경로로 간다)
    """
    counter = {"judge_calls": 0, "retrieval_calls": 0}

    def fake_retrieval(state):
        counter["retrieval_calls"] += 1
        return {"context": "가짜 context", "retrieved_sources": ["fake.md"]}

    def fake_judge(state):
        i = min(counter["judge_calls"], len(judge_scores) - 1)
        score = judge_scores[i]
        counter["judge_calls"] += 1
        return {
            "evaluation_result": EvaluationResult(
                technical_score=score,
                completeness_score=score,
                strengths=["강점"],
                improvements=["개선점"],
                overall_feedback="피드백",
            )
        }

    def fake_learning_tip(state):
        return {"learning_tip": LearningTip(topic="주제", reason="이유", recommended_sections=["절"])}

    def fake_followup(state):
        question = f"꼬리질문-{state.get('turn', 1)}"
        return {
            "next_action": "followup_generated",
            "followup_question": question,
            "next_question": question,
        }

    def fake_advanced(state):
        question = f"심화질문-{state.get('turn', 1)}"
        return {
            "next_action": "advanced_question_generated",
            "advanced_question": AdvancedQuestion(question=question, intent="의도"),
            "next_question": question,
        }

    def fake_fundamentals(state):
        return {
            "next_action": "fundamentals_explained",
            "concept_explanation": ConceptExplanation(
                concept="개념", explanation="설명", key_points=["포인트"]
            ),
        }

    # build_interview_session_graph()가 읽는 것은 rag.graph 모듈의 전역 이름이므로
    # 원본 모듈이 아니라 여기를 갈아끼워야 한다.
    monkeypatch.setattr(graph_module, "retrieval_node", fake_retrieval)
    monkeypatch.setattr(graph_module, "judge_node", fake_judge)
    monkeypatch.setattr(graph_module, "learning_tip_node", fake_learning_tip)
    monkeypatch.setattr(graph_module, "followup_node", fake_followup)
    monkeypatch.setattr(graph_module, "advanced_question_node", fake_advanced)
    monkeypatch.setattr(graph_module, "fundamentals_node", fake_fundamentals)
    return counter


def _start(graph, thread_id="t"):
    config = {"configurable": {"thread_id": thread_id}}
    graph.invoke({"question": "첫 질문", "answer": "첫 답변", "turn": 1}, config=config)
    return config


def test_코칭_후_사용자_답변을_기다리며_멈춘다(monkeypatch):
    _patch_nodes(monkeypatch, [5])
    graph = graph_module.build_interview_session_graph()
    config = _start(graph)

    snapshot = graph.get_state(config)
    # next가 비어 있지 않다 = 아직 끝나지 않고 await_answer에서 멈춰 있다
    assert snapshot.next == ("await_answer",)
    assert snapshot.values["turn"] == 1
    assert snapshot.values["next_question"] == "꼬리질문-1"


def test_답변을_주면_사이클이_돌아_다시_채점한다(monkeypatch):
    counter = _patch_nodes(monkeypatch, [5, 5])
    graph = graph_module.build_interview_session_graph()
    config = _start(graph)

    assert counter["judge_calls"] == 1

    graph.invoke(Command(resume="두 번째 답변"), config=config)
    snapshot = graph.get_state(config)

    # 사이클의 증거: 같은 세션에서 retrieval과 judge가 한 번 더 실행됐다
    assert counter["judge_calls"] == 2
    assert counter["retrieval_calls"] == 2
    assert snapshot.values["turn"] == 2
    # 다음 턴의 질문이 직전 꼬리질문으로 교체됐다
    assert snapshot.values["question"] == "꼬리질문-1"
    assert snapshot.values["answer"] == "두 번째 답변"


def test_이전_턴이_history에_누적된다(monkeypatch):
    _patch_nodes(monkeypatch, [5, 6])
    graph = graph_module.build_interview_session_graph()
    config = _start(graph)
    graph.invoke(Command(resume="두 번째 답변"), config=config)

    history = graph.get_state(config).values["history"]
    assert len(history) == 1
    assert history[0]["turn"] == 1
    assert history[0]["question"] == "첫 질문"
    assert history[0]["answer"] == "첫 답변"
    assert history[0]["technical_score"] == 5


def test_MAX_TURNS에_도달하면_종료된다(monkeypatch):
    counter = _patch_nodes(monkeypatch, [5] * (MAX_TURNS + 1))
    graph = graph_module.build_interview_session_graph()
    config = _start(graph)

    # MAX_TURNS까지 답변을 계속 제출
    for i in range(MAX_TURNS - 1):
        assert graph.get_state(config).next, f"{i + 1}턴에서 이미 종료되면 안 된다"
        graph.invoke(Command(resume=f"답변{i + 2}"), config=config)

    snapshot = graph.get_state(config)
    assert snapshot.values["turn"] == MAX_TURNS
    assert snapshot.next == ()          # 더 기다리지 않고 종료
    assert counter["judge_calls"] == MAX_TURNS
    assert len(snapshot.values["history"]) == MAX_TURNS - 1


def test_기초개념_경로는_루프하지_않고_바로_끝난다(monkeypatch):
    counter = _patch_nodes(monkeypatch, [1])
    graph = graph_module.build_interview_session_graph()
    config = _start(graph)

    snapshot = graph.get_state(config)
    # 0~3점은 다음 질문을 만들지 않으므로 사이클을 타지 않는다
    assert snapshot.next == ()
    assert snapshot.values["next_action"] == "fundamentals_explained"
    assert "next_question" not in snapshot.values
    assert counter["judge_calls"] == 1


def test_심화질문_경로도_루프한다(monkeypatch):
    counter = _patch_nodes(monkeypatch, [9, 9])
    graph = graph_module.build_interview_session_graph()
    config = _start(graph)

    assert graph.get_state(config).values["next_question"] == "심화질문-1"

    graph.invoke(Command(resume="두 번째 답변"), config=config)
    snapshot = graph.get_state(config)

    assert counter["judge_calls"] == 2
    assert snapshot.values["turn"] == 2
    assert snapshot.values["question"] == "심화질문-1"


def test_세션끼리_상태가_섞이지_않는다(monkeypatch):
    _patch_nodes(monkeypatch, [5, 5])
    graph = graph_module.build_interview_session_graph()

    config_a = _start(graph, thread_id="세션A")
    config_b = _start(graph, thread_id="세션B")

    graph.invoke(Command(resume="A의 두 번째 답변"), config=config_a)

    # thread_id로 분리되므로 A만 2턴이고 B는 1턴에 멈춰 있어야 한다
    assert graph.get_state(config_a).values["turn"] == 2
    assert graph.get_state(config_b).values["turn"] == 1
    assert graph.get_state(config_a).values["answer"] == "A의 두 번째 답변"


@pytest.mark.parametrize("turn,expected", [(1, "continue"), (MAX_TURNS - 1, "continue"), (MAX_TURNS, "end")])
def test_계속_판단_함수를_경계값에서_검증한다(turn, expected):
    from rag.graph_nodes import decide_continue

    # 라우팅이 순수 함수라 LLM 없이 경계값을 직접 검증할 수 있다
    assert decide_continue({"turn": turn}) == expected
