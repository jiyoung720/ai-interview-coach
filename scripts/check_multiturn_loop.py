"""멀티턴 루프(Phase 11) 실행 검증.

그래프에 사이클이 생겼으므로, 구조 검증(테스트)만으로는 "실제로 되돌아가서
다시 채점하는가"를 확인할 수 없다. 이 스크립트는 실제 Gemini를 호출해
세션이 턴을 넘기며 이어지는지, 종료 조건에서 멈추는지를 확인한다.

실행: uv run python scripts/check_multiturn_loop.py
"""

import uuid

from langgraph.types import Command

from rag.graph import build_interview_session_graph
from rag.graph_nodes import MAX_TURNS


def run_session(first_question: str, answers: list[str]) -> None:
    """첫 질문에 대해 답변을 순서대로 제출하며 세션을 진행한다."""
    graph = build_interview_session_graph()
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}

    graph.invoke({"question": first_question, "answer": answers[0], "turn": 1}, config=config)

    for next_answer in answers[1:]:
        snapshot = graph.get_state(config)
        if not snapshot.next:
            break   # 이미 종료된 세션이면 더 보내지 않는다
        _report_turn(snapshot)
        print(f"    -> 사용자 답변 제출: {next_answer[:40]}...")
        graph.invoke(Command(resume=next_answer), config=config)

    _report_turn(graph.get_state(config), final=True)


def _report_turn(snapshot, final: bool = False) -> None:
    values = snapshot.values
    awaiting = bool(snapshot.next)
    evaluation = values["evaluation_result"]

    label = "최종" if final else "진행"
    print(f"  [{label}] turn={values.get('turn')} "
          f"technical={evaluation.technical_score} "
          f"경로={values.get('next_action')} "
          f"상태={'대기중' if awaiting else '종료'}")
    if awaiting:
        print(f"    다음 질문: {values.get('next_question', '')[:70]}...")
    else:
        print(f"    누적 history: {len(values.get('history', []))}턴")


if __name__ == "__main__":
    print(f"MAX_TURNS = {MAX_TURNS}\n")

    print("[케이스 1] 부분 이해(4~6점 예상) -> 꼬리질문 -> 재답변 루프")
    run_session(
        "JWT란 무엇이고 어떻게 동작하나요?",
        [
            "JWT는 토큰 기반 인증 방식입니다. 로그인하면 서버가 토큰을 주고 그걸로 인증합니다.",
            "JWT는 Header, Payload, Signature 세 부분으로 구성되고 점으로 구분됩니다. Signature로 위변조를 검증합니다.",
            "Signature는 Header와 Payload를 secret key로 서명한 값이라, 내용이 바뀌면 검증에 실패합니다.",
        ],
    )

    print("\n[케이스 2] 개념 모름(0~3점 예상) -> 루프 없이 종료되어야 함")
    run_session(
        "JWT란 무엇이고 어떻게 동작하나요?",
        ["잘 모르겠습니다."],
    )
