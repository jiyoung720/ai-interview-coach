from langgraph.graph import END, START, StateGraph

from rag.graph_nodes import (
    decide_next_step,
    followup_node,
    generation_node,
    judge_node,
    learning_tip_node,
    retrieval_node,
    user_docs_retrieval_node,
)
from rag.graph_state import InterviewState


def build_retrieval_only_graph():
    """RAGAS 평가 등 context만 필요할 때 쓰는 그래프.
    Judge/Learning Tip/Followup까지 다 도는 build_interview_agent_graph()를 쓰면
    필요 없는 Gemini 호출이 같이 발생하므로, retrieval만 도는 최소 그래프를 따로 둠."""
    graph = StateGraph(InterviewState)
    graph.add_node("retrieval", retrieval_node)
    graph.add_edge(START, "retrieval")
    graph.add_edge("retrieval", END)
    return graph.compile()


def build_chain_b_graph():
    """Agent 분기 없이 Judge 점수만 필요할 때 쓰는 그래프 (예: Calibration Set 채점).
    전체 Chain B 그래프: Retrieval(Interview KB) → Judge"""
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
    """Chain B + Agent v2: Retrieval → Judge → Decision → (< 5) → Learning Tip → Followup → END

    Learning Tip이 먼저 실행되어 핵심 약점(topic)을 정하고,
    Followup이 그 topic을 그대로 이어받아 겨냥한 꼬리질문을 만든다.
    두 노드가 같은 improvements를 각자 따로 해석하지 않고, 순차적으로 하나의
    진단 결과를 공유하도록 설계했다."""
    graph = StateGraph(InterviewState)
    graph.add_node("retrieval", retrieval_node)
    graph.add_node("judge", judge_node)
    graph.add_node("learning_tip", learning_tip_node)
    graph.add_node("followup", followup_node)

    graph.add_edge(START, "retrieval")
    graph.add_edge("retrieval", "judge")
    graph.add_conditional_edges(
        "judge",
        decide_next_step,
        {"learning_tip": "learning_tip", "end": END},
    )
    graph.add_edge("learning_tip", "followup")
    graph.add_edge("followup", END)

    return graph.compile()
