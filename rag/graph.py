# 노드들을 서로 다른 순서로 이어 그래프 4개를 조립하는 공장.
# 서비스용은 2개(chain_a=질문생성, interview_agent=답변평가+Agent)이고,
# 나머지 2개(retrieval_only, chain_b)는 평가/실험에서 불필요한 LLM 호출을 피하려는 축소판임
from langgraph.graph import END, START, StateGraph

from rag.graph_nodes import (
    advanced_question_node,
    await_answer_node,
    decide_continue,
    decide_next_step,
    decide_scope,
    followup_node,
    fundamentals_node,
    generation_node,
    judge_node,
    learning_tip_node,
    out_of_scope_node,
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
    graph.add_node("out_of_scope", out_of_scope_node)

    graph.add_edge(START, "retrieval")   # 시작 -> KB 검색
    # 채점보다 먼저 판단한다. KB에 근거가 없으면 judge를 아예 부르지 않는다 (Phase 17)
    graph.add_conditional_edges(
        "retrieval",
        decide_scope,
        {
            "in_scope": "judge",
            "out_of_scope": "out_of_scope",
        },
    )
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
    graph.add_edge("out_of_scope", END)         # 근거 없음 경로 종료 (점수 없음)
    graph.add_edge("fundamentals", END)         # 0~3점 경로 종료
    graph.add_edge("learning_tip", "followup")  # 팁 -> 꼬리질문 (순차)
    graph.add_edge("followup", END)             # 4~6점 경로 종료
    graph.add_edge("advanced", END)             # 7~10점 경로 종료

    return graph.compile()


def build_interview_session_graph(checkpointer=None):
    """Phase 11: 멀티턴 면접 루프. 위 그래프에 사이클을 추가한 버전.

    구조:
        START -> retrieval -> judge -> [점수 구간별 3분기]
            0~3점 : fundamentals -> END          (다음 질문이 없어 루프하지 않음)
            4~6점 : learning_tip -> followup ->|
            7~10점: advanced ----------------->| decide_continue
                                                    "end"      -> END
                                                    "continue" -> await_answer
        await_answer -> retrieval  (여기가 사이클)

    build_interview_agent_graph()와 노드는 전부 공유하고 배선만 다르다.
    기존 그래프를 고치지 않고 따로 둔 이유는, 단발성 호출(`POST /evaluate-answer`)과
    Calibration 스크립트들이 그대로 동작해야 하기 때문이다.

    **이 그래프가 LangGraph를 쓰는 근거다.** 지금까지의 구조(조건부 분기 + 순차 실행)는
    LCEL의 RunnableBranch로도 표현할 수 있었지만, "코칭 -> 사용자 재답변 -> 다시 채점"으로
    되돌아오는 사이클과 그 중간에서 실행을 멈췄다 재개하는 동작은 LCEL로는 만들 수 없다.

    0~3점 경로만 루프에서 빠지는 이유: fundamentals는 개념을 설명할 뿐 다음 질문을
    만들지 않는다. 개념 자체를 모르는 상태에서 같은 주제로 재질문하는 것이
    코칭으로서 적절하지 않다고 보고, 설명을 주고 세션을 마치도록 했다."""
    graph = StateGraph(InterviewState)
    graph.add_node("retrieval", retrieval_node)
    graph.add_node("judge", judge_node)
    graph.add_node("fundamentals", fundamentals_node)
    graph.add_node("learning_tip", learning_tip_node)
    graph.add_node("followup", followup_node)
    graph.add_node("advanced", advanced_question_node)
    graph.add_node("await_answer", await_answer_node)   # 사이클의 연결점 (interrupt)
    graph.add_node("out_of_scope", out_of_scope_node)

    graph.add_edge(START, "retrieval")
    # 근거가 없으면 채점하지 않고 END로 간다. 세션을 이어갈지는 사용자가 정하므로(Phase 17)
    # 그래프 안에서 자동으로 루프하지 않고, API가 새 질문을 받아 다음 턴을 시작한다.
    graph.add_conditional_edges(
        "retrieval",
        decide_scope,
        {
            "in_scope": "judge",
            "out_of_scope": "out_of_scope",
        },
    )
    graph.add_edge("out_of_scope", END)
    graph.add_conditional_edges(
        "judge",
        decide_next_step,
        {
            "fundamentals": "fundamentals",
            "learning_tip": "learning_tip",
            "advanced": "advanced",
        },
    )
    graph.add_edge("fundamentals", END)
    graph.add_edge("learning_tip", "followup")

    # 다음 질문을 만든 두 경로만 "한 턴 더 갈지"를 판단한다
    for coaching_node in ("followup", "advanced"):
        graph.add_conditional_edges(
            coaching_node,
            decide_continue,
            {"continue": "await_answer", "end": END},
        )

    # 사이클: 새 답변을 받았으니 검색부터 다시 (질문이 바뀌었으므로 context도 새로 뽑아야 함)
    graph.add_edge("await_answer", "retrieval")

    # interrupt로 멈춘 State를 보관할 곳. 이게 없으면 재개할 수 없어 사이클이 성립하지 않는다
    return graph.compile(checkpointer=checkpointer or _build_checkpointer())


def _build_checkpointer():
    """세션 State를 보관할 checkpointer.

    State에 Pydantic 객체(EvaluationResult 등)가 들어가는데, LangGraph 기본 설정은
    저장·복원 시 "모든 타입을 허용하되 경고를 띄우는" 상태다. 이 기본값은 향후 버전에서
    차단될 예정이라고 경고가 명시하고 있어, 우리가 쓰는 스키마만 명시적으로 등록해둔다.

    보안 측면에서도 명시적 허용이 맞다. checkpoint 저장소에 접근할 수 있는 공격자가
    임의 객체를 넣어 역직렬화 시점에 코드를 실행시키는 경로를 막아준다."""
    from langgraph.checkpoint.memory import MemorySaver
    from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

    from rag.schemas import (
        AdvancedQuestion,
        ConceptExplanation,
        EvaluationResult,
        LearningTip,
    )

    serde = JsonPlusSerializer(
        allowed_msgpack_modules=[
            EvaluationResult,
            LearningTip,
            ConceptExplanation,
            AdvancedQuestion,
        ]
    )
    return MemorySaver(serde=serde)


# 세션 그래프는 요청마다 새로 만들면 안 된다. checkpointer(대화 상태)가 함께
# 새로 만들어져서, 이전 턴의 State를 찾지 못하기 때문이다.
_session_graph = None


def get_interview_session_graph():
    """멀티턴 세션 그래프의 프로세스 단위 싱글턴."""
    global _session_graph
    if _session_graph is None:
        _session_graph = build_interview_session_graph()
    return _session_graph
