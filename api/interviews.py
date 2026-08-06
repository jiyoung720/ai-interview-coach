# 멀티턴 면접 세션 엔드포인트 (Phase 11)
# 단발성인 POST /evaluate-answer와 달리, 한 세션 안에서 여러 턴을 주고받는다.
# 그래프가 interrupt로 멈춘 자리를 checkpointer가 기억하고 있어서,
# 다음 요청이 오면 멈춘 지점부터 이어서 실행된다.
import uuid

from fastapi import APIRouter, HTTPException
from langgraph.types import Command
from pydantic import BaseModel

from rag.graph import get_interview_session_graph
from rag.graph_nodes import MAX_TURNS

router = APIRouter(prefix="/interview")


class StartSessionRequest(BaseModel):
    question: str   # 첫 면접 질문
    answer: str     # 그에 대한 사용자 답변


class ContinueSessionRequest(BaseModel):
    session_id: str
    answer: str     # 직전 턴에서 받은 질문에 대한 답변
    # 범위 밖으로 보류된 세션을 이어갈 때만 쓴다. 그때는 재개할 지점이 없어
    # 다음 질문을 새로 받아야 한다 (Phase 17)
    question: str | None = None


OUT_OF_SCOPE_MESSAGE = (
    "현재 고정 지식에 검증 가능한 근거가 없어 정확한 평가를 보류합니다. "
    "이 경험을 평가받고 싶다면 관련 문서를 업로드해 주세요."
)


def _coaching_payload(values: dict, out_of_scope: bool = False) -> dict:
    """점수 구간에 따라 셋 중 하나만 채워지는 코칭 결과를 꺼낸다.
    실행되지 않은 경로의 키는 State에 아예 없으므로 .get()으로 조회한다.

    범위 밖 턴에서는 전부 비운다. State는 턴을 넘어 누적되므로 그냥 꺼내면
    직전 턴의 코칭이 이번 턴 결과인 것처럼 나가기 때문이다."""
    if out_of_scope:
        return {
            "concept_explanation": None,
            "learning_tip": None,
            "followup_question": None,
            "advanced_question": None,
        }

    concept = values.get("concept_explanation")
    tip = values.get("learning_tip")
    advanced = values.get("advanced_question")
    return {
        "concept_explanation": concept.model_dump() if concept else None,
        "learning_tip": tip.model_dump() if tip else None,
        "followup_question": values.get("followup_question"),
        "advanced_question": advanced.model_dump() if advanced else None,
    }


def _end_reason(values: dict) -> str:
    """루프가 왜 끝났는지 판단한다. 종료 조건을 한 곳에 모아 응답으로 드러낸다."""
    if values.get("out_of_scope"):
        # 채점을 보류했을 뿐 면접이 끝난 것은 아니다. 이어갈지는 사용자가 정한다
        return "out_of_scope"
    if values.get("next_action") == "fundamentals_explained":
        # 0~3점 경로는 다음 질문을 만들지 않으므로 애초에 사이클을 타지 않는다
        return "fundamentals_no_followup"
    if values.get("turn", 1) >= MAX_TURNS:
        return "max_turns_reached"
    return "completed"


def _turn_response(session_id: str, snapshot) -> dict:
    """한 턴의 실행 결과를 응답 형태로 조립한다.

    snapshot.next가 비어 있지 않다는 것은 그래프가 아직 끝나지 않고
    await_answer에서 멈춰 사용자 답변을 기다린다는 뜻이다."""
    values = snapshot.values
    awaiting = bool(snapshot.next)

    # 범위 밖이면 judge를 아예 거치지 않았으므로 평가 결과가 없다 (Phase 17).
    # 점수를 0으로 채워 내려보내지 않는다. 사용자가 그 값을 자기 실력으로 읽으면 곤란하다.
    out_of_scope = values.get("out_of_scope", False)
    evaluation = values.get("evaluation_result")

    if out_of_scope:
        status = "out_of_scope"
    elif awaiting:
        status = "awaiting_answer"
    else:
        status = "completed"

    return {
        "session_id": session_id,
        # 범위 밖 턴은 면접 턴으로 세지 않으므로 turn이 늘지 않는다
        "turn": values.get("turn", 1),
        "max_turns": MAX_TURNS,
        # awaiting_answer면 next_question에 답을 보내 세션을 이어갈 수 있다
        "status": status,
        "evaluation": evaluation.model_dump() if evaluation and not out_of_scope else None,
        "out_of_scope_message": OUT_OF_SCOPE_MESSAGE if out_of_scope else None,
        "retrieved_sources": values.get("retrieved_sources", []),
        "next_action": values.get("next_action"),
        **_coaching_payload(values, out_of_scope),
        "next_question": values.get("next_question") if awaiting and not out_of_scope else None,
        "end_reason": None if awaiting else _end_reason(values),
        "history": values.get("history", []),
    }


@router.post("/start")
def start_session(request: StartSessionRequest):
    """새 면접 세션을 시작한다. 첫 질문과 답변을 받아 1턴을 실행한다."""
    graph = get_interview_session_graph()
    session_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": session_id}}

    graph.invoke(
        {"question": request.question, "answer": request.answer, "turn": 1},
        config=config,
    )
    return _turn_response(session_id, graph.get_state(config))


@router.post("/answer")
def continue_session(request: ContinueSessionRequest):
    """진행 중인 세션에 다음 답변을 제출해 한 턴 더 진행한다."""
    graph = get_interview_session_graph()
    config = {"configurable": {"thread_id": request.session_id}}

    snapshot = graph.get_state(config)
    if not snapshot.created_at:
        # checkpointer가 메모리 기반이라, 서버가 재시작되면 이전 세션은 사라진다
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다. 새로 시작해주세요.")

    if snapshot.values.get("out_of_scope"):
        # 범위 밖 턴은 채점 없이 END까지 갔으므로 재개할 interrupt가 없다.
        # 사용자가 "계속하기"를 골랐다면 새 질문을 받아 같은 세션에서 한 턴을 다시 시작한다.
        if not request.question:
            raise HTTPException(
                status_code=400,
                detail="근거가 없어 보류된 세션입니다. 계속하려면 다른 질문을 함께 보내주세요.",
            )
        graph.invoke(
            {
                "question": request.question,
                "answer": request.answer,
                # 범위 밖 턴은 카운트하지 않으므로 직전 턴 번호를 그대로 이어받는다
                "turn": snapshot.values.get("turn", 1),
                "out_of_scope": False,
            },
            config=config,
        )
        return _turn_response(request.session_id, graph.get_state(config))

    if not snapshot.next:
        raise HTTPException(status_code=409, detail="이미 종료된 세션입니다.")

    # 멈춰 있던 interrupt()에 답변을 돌려주며 재개한다.
    # 그래프는 await_answer 다음의 retrieval로 이어져 새 질문으로 다시 채점한다.
    graph.invoke(Command(resume=request.answer), config=config)
    return _turn_response(request.session_id, graph.get_state(config))
