# 노드들을 서로 다른 순서로 이어 그래프 4개를 조립하는 공장.
# 서비스용은 2개(chain_a=질문생성, interview_agent=답변평가+Agent)이고,
# 나머지 2개(retrieval_only, chain_b)는 평가/실험에서 불필요한 LLM 호출을 피하려는 축소판임
from langgraph.graph import END, START, StateGraph

from rag.graph_nodes import (
    advanced_question_node,
    decide_next_step,
    followup_node,
    fundamentals_node,
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
    # LangGraph 4단계 API (모든 빌더가 이 패턴을 공유함)
    graph = StateGraph(InterviewState)            # 01. 빈 그래프 생성 (State 스키마 지정)
    graph.add_node("retrieval", retrieval_node)   # 02. 노드 추가 ("이름"에 함수를 등록)
    graph.add_edge(START, "retrieval")            # 03. 엣지 추가 (START 다음 retrieval로)
    graph.add_edge("retrieval", END)              # retrieval 다음 END로
    return graph.compile()                        # 04. 실행 가능한 형태로 완성 (.invoke 가능)


def build_chain_b_graph():
    """Agent 분기 없이 Judge 점수만 필요할 때 쓰는 그래프 (예: Calibration Set 채점).
    전체 Chain B 그래프: Retrieval(Interview KB) → Judge"""
    graph = StateGraph(InterviewState)
    graph.add_node("retrieval", retrieval_node)
    graph.add_node("judge", judge_node)
    graph.add_edge(START, "retrieval")  # 시작 → 검색
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
    """Chain B + Agent v3: Retrieval → Judge → Decision → 점수 구간별 3분기 → END

    0~3점: Fundamentals(기초 개념 설명)
    4~6점: Learning Tip → Followup (순차)
    7~10점: Advanced Question(심화 질문)

    v2까지는 "5점 미만이면 코칭, 아니면 아무것도 안 함"이라 분기가 단조롭고
    한쪽 경로가 비어 있었다. 구간별로 필요한 코칭의 종류가 다르다고 보고
    세 갈래로 확장해, 모든 점수대에서 결과가 나오도록 했다.

    4~6점 경로에서 Learning Tip이 먼저 실행되어 핵심 약점(topic)을 정하고,
    Followup이 그 topic을 그대로 이어받아 겨냥한 꼬리질문을 만든다.
    두 노드가 같은 improvements를 각자 따로 해석하지 않고, 순차적으로 하나의
    진단 결과를 공유하도록 설계했다."""
    graph = StateGraph(InterviewState)
    graph.add_node("retrieval", retrieval_node)
    graph.add_node("judge", judge_node)
    graph.add_node("fundamentals", fundamentals_node)
    graph.add_node("learning_tip", learning_tip_node)
    graph.add_node("followup", followup_node)
    graph.add_node("advanced", advanced_question_node)

    graph.add_edge(START, "retrieval")   # 시작 -> KB 검색
    graph.add_edge("retrieval", "judge") # 검색 -> 채점
    # 여기가 Agent의 심장: 일반 add_edge와 달리 다음 노드가 런타임에 결정됨
    graph.add_conditional_edges(
        "judge",              # 이 노드가 끝난 직후 분기 판단
        decide_next_step,     # 판단 함수 (문자열 반환)
        {                     # 반환값 -> 실제 목적지 매핑
            "fundamentals": "fundamentals",
            "learning_tip": "learning_tip",
            "advanced": "advanced",
        },
    )
    graph.add_edge("fundamentals", END)         # 0~3점 경로 종료
    graph.add_edge("learning_tip", "followup")  # 팁 -> 꼬리질문 (순차)
    graph.add_edge("followup", END)             # 4~6점 경로 종료
    graph.add_edge("advanced", END)             # 7~10점 경로 종료

    return graph.compile()
