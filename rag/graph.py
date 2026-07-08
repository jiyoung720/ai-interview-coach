from langgraph.graph import END, START, StateGraph

from rag.graph_nodes import (
    decide_followup,
    followup_node,
    generation_node,
    judge_node,
    retrieval_node,
    user_docs_retrieval_node,
)
from rag.graph_state import InterviewState


def build_retrieval_only_graph():
    """Retrieval Node만 있는 최소 그래프. Judge Node를 붙이기 전
    context/retrieved_sources가 정상적으로 채워지는지 단독 검증용."""
    graph = StateGraph(InterviewState)
    graph.add_node("retrieval", retrieval_node)
    graph.add_edge(START, "retrieval")
    graph.add_edge("retrieval", END)
    return graph.compile()


def build_chain_b_graph():
    """전체 Chain B 그래프: Retrieval(Interview KB) → Judge"""
    graph = StateGraph(InterviewState)
    graph.add_node("retrieval", retrieval_node)
    graph.add_node("judge", judge_node)
    graph.add_edge(START, "retrieval")
    graph.add_edge("retrieval", "judge")
    graph.add_edge("judge", END)
    return graph.compile()


def build_chain_a_graph():
    """전체 Chain A 그래프: Retrieval(User Docs) → Generation"""
    graph = StateGraph(InterviewState)
    graph.add_node("retrieval", user_docs_retrieval_node)
    graph.add_node("generation", generation_node)
    graph.add_edge(START, "retrieval")
    graph.add_edge("retrieval", "generation")
    graph.add_edge("generation", END)
    return graph.compile()


def build_interview_agent_graph():
    """Chain B + 조건부 분기: Retrieval → Judge → (technical_score 낮으면) Followup

    이게 이 프로젝트의 첫 Agent 형태 - 고정된 파이프라인이 아니라
    State(evaluation_result)에 따라 다음 행동이 갈린다."""
    graph = StateGraph(InterviewState)
    graph.add_node("retrieval", retrieval_node)
    graph.add_node("judge", judge_node)
    graph.add_node("followup", followup_node)

    graph.add_edge(START, "retrieval")
    graph.add_edge("retrieval", "judge")
    graph.add_conditional_edges(
        "judge",
        decide_followup,
        {"followup": "followup", "end": END},
    )
    graph.add_edge("followup", END)

    return graph.compile()
