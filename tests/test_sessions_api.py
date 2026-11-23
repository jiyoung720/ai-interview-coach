"""세션 API와 재시도 계약 (M0 S4).

설계 §5.4의 재시도 시나리오를 HTTP 수준에서 확인한다. 엔진은 가짜 판정 골격이고,
외부 모델 호출은 호출 횟수만 세는 가짜로 대신해 API 키 없이 돈다.
"""
import threading

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from core import llm
from core.budget import BudgetGate
from core.config import load_settings
from core.transitions import ACTIONS, ALLOWED_ACTIONS, can_act, status_after, status_after_plan
from rag.v2.turn_graph import JudgeFailed, SkeletonEngine


def make_client(tmp_path, engine=None, mode="demo", budget=300):
    settings = load_settings({"APP_MODE": mode, "SECRET_KEY": "test-secret", "DATA_DIR": str(tmp_path),
                              "DAILY_LLM_BUDGET": str(budget)})
    # 데모 모드 쿠키는 Secure라 https로 요청해야 쿠키가 돌아온다 (공개 서버와 같은 조건)
    return TestClient(create_app(settings, engine=engine or SkeletonEngine()), base_url="https://testserver")


def create(client, key="c1", **body):
    return client.post("/sessions", json=body or {"sample_id": "s1"}, headers={"Idempotency-Key": key})


def event(client, session, key, action="answer", answer="답변"):
    payload = {"question_id": session["current_question"]["id"], "version": session["version"], "action": action}
    if action == "answer":
        payload["answer"] = answer
    return client.post(f"/sessions/{session['session_id']}/events", json=payload, headers={"Idempotency-Key": key})


def test_생성과_답변과_종료의_기본_흐름(tmp_path):
    with make_client(tmp_path) as client:
        session = create(client).json()
        assert session["status"] == "awaiting_answer" and session["current_question"]["id"] == "q1"

        first = event(client, session, "e1").json()
        assert first["turn"]["event"] == "answered" and first["next_question"]["id"] == "q2"

        current = client.get(f"/sessions/{session['session_id']}").json()
        ended = event(client, current, "e2", action="end").json()
        assert ended["status"] == "done" and ended["turn"]["event"] == "ended"


def test_넘기기는_판정_없이_다음_메인으로(tmp_path):
    with make_client(tmp_path) as client:
        session = create(client).json()
        skipped = event(client, session, "e1", action="skip").json()
        assert skipped["turn"]["event"] == "skipped" and skipped["turn"]["judgement"] is None
        assert skipped["next_question"]["id"] == "q2"


def test_멱등_키가_없으면_400(tmp_path):
    with make_client(tmp_path) as client:
        assert client.post("/sessions", json={"sample_id": "s1"}).status_code == 400


def test_s1_커밋_후_응답_유실_같은_키_재전송은_같은_응답(tmp_path):
    with make_client(tmp_path) as client:
        session = create(client).json()
        first = event(client, session, "e1").json()
        again = event(client, session, "e1").json()   # 같은 키 + 같은 본문
        assert again == first
        assert len(client.get(f"/sessions/{session['session_id']}").json()["turns"]) == 1


def test_s4_같은_키에_다른_본문은_422(tmp_path):
    with make_client(tmp_path) as client:
        session = create(client).json()
        event(client, session, "e1", answer="A")
        assert event(client, session, "e1", answer="B").status_code == 422


def test_s5_선행_요청_커밋_후_같은_키는_409가_아니라_저장된_응답(tmp_path):
    with make_client(tmp_path) as client:
        session = create(client).json()
        first = event(client, session, "e1")
        # session은 이전 버전을 들고 있다. 같은 키라서 버전 검사보다 멱등 조회가 먼저다
        resent = event(client, session, "e1")
        assert first.status_code == resent.status_code == 200
        assert resent.json() == first.json()
        # 다른 키로 옛 버전을 보내면 그때는 409
        assert event(client, session, "e2").status_code == 409


def test_s3_같은_세션에_동시_요청_두_개는_하나만_반영된다(tmp_path):
    entered, release = threading.Event(), threading.Event()

    def slow_judge(question, text):
        entered.set()
        release.wait(5)
        return {"diagnosis": "solid"}

    with make_client(tmp_path, SkeletonEngine(judge=slow_judge)) as client:
        session = create(client).json()
        results = {}
        first = threading.Thread(target=lambda: results.update(a=event(client, session, "k-a")))
        first.start()
        entered.wait(5)
        second = threading.Thread(target=lambda: results.update(b=event(client, session, "k-b")))
        second.start()
        release.set()
        first.join(5)
        second.join(5)

        assert results["a"].status_code == 200
        assert results["b"].status_code == 409            # 잠금이 풀린 뒤 버전이 이미 올라가 있다
        assert len(client.get(f"/sessions/{session['session_id']}").json()["turns"]) == 1


def test_s6_s7_같은_생성_키는_세션도_방문자_차감도_계획도_한_번(tmp_path):
    plans = {"n": 0}

    def counting_planner(request):
        plans["n"] += 1
        return [{"id": "q1", "text": "질문", "depth": 0}]

    with make_client(tmp_path, SkeletonEngine(planner=counting_planner)) as client:
        client.get("/health")             # 실제 브라우저처럼 owner_id 쿠키를 먼저 받는다
        responses = []
        threads = [threading.Thread(target=lambda: responses.append(create(client, "same"))) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        ids = {r.json()["session_id"] for r in responses}
        assert len(ids) == 1 and plans["n"] == 1

        # 방문자 차감도 1회: 같은 브라우저로 서로 다른 키 2개를 더 만들 수 있다(상한 3)
        assert create(client, "k2").status_code == 200
        assert create(client, "k3").status_code == 200
        assert create(client, "k4").status_code == 429


def test_방문자별_세션_상한은_로컬_모드에_적용하지_않는다(tmp_path):
    with make_client(tmp_path, mode="local") as client:
        for i in range(5):
            assert create(client, f"k{i}").status_code == 200


def test_판정_전_예산_소진이면_429이고_아무것도_기록하지_않는다(tmp_path):
    with make_client(tmp_path, budget=0) as client:
        session = create(client).json()
        assert event(client, session, "e1").status_code == 429
        state = client.get(f"/sessions/{session['session_id']}").json()
        assert state["turns"] == [] and state["version"] == session["version"]


def test_s8_판정_후_예산_소진이면_판정은_보존하고_다음_메인으로(tmp_path):
    from core.llm import BudgetedModel

    class Echo:
        def invoke(self, input, config=None, **kwargs):
            return "코칭"

    model = BudgetedModel(Echo(), max_attempts=1)

    def judge(question, text):
        model.invoke("판정 요청")                 # 실제 판정처럼 외부 호출 1회 (예약분을 쓴다)
        return {"diagnosis": "partial" if "모름" in text else "solid"}

    def coach(question, judgement):
        return {"text": model.invoke("코칭 요청")}

    # 예산 1: 판정 예약에 쓰이고, 코칭 호출에서 소진
    with make_client(tmp_path, SkeletonEngine(judge=judge, coach=coach), budget=1) as client:
        session = create(client).json()
        result = event(client, session, "e1", answer="잘 모름").json()   # partial이라 원래는 꼬리질문
        assert result["turn"]["judgement"] == {"diagnosis": "partial"}
        assert result["turn"]["coaching_skipped"] is True
        assert result["next_question"]["id"] == "q2"                   # 꼬리질문 대신 다음 메인


def test_판정_실패는_judge_failed로_기록하고_다음_메인으로(tmp_path):
    def failing_judge(question, text):
        raise JudgeFailed()

    with make_client(tmp_path, SkeletonEngine(judge=failing_judge)) as client:
        session = create(client).json()
        result = event(client, session, "e1").json()
        assert result["turn"]["event"] == "judge_failed" and result["next_question"]["id"] == "q2"


def test_답변_길이_상한은_서버에서_거부(tmp_path):
    with make_client(tmp_path) as client:
        session = create(client).json()
        assert event(client, session, "e1", answer="가" * 2001).status_code == 400


def test_남의_세션은_404(tmp_path):
    with make_client(tmp_path) as client:
        session = create(client).json()
    with make_client(tmp_path) as stranger:                # 쿠키가 없는 새 브라우저
        assert stranger.get(f"/sessions/{session['session_id']}").status_code == 404
        assert stranger.delete(f"/sessions/{session['session_id']}").status_code == 404


def test_삭제하면_404(tmp_path):
    with make_client(tmp_path) as client:
        session = create(client).json()
        assert client.delete(f"/sessions/{session['session_id']}").status_code == 204
        assert client.get(f"/sessions/{session['session_id']}").status_code == 404


@pytest.mark.parametrize("status", list(ALLOWED_ACTIONS))
@pytest.mark.parametrize("action", ACTIONS)
def test_전이표_전수(status, action):
    assert can_act(status, action) == (status == "awaiting_answer")


def test_전이_결과():
    assert status_after("judged", {"id": "q2"}) == "awaiting_answer"
    assert status_after("judged", None) == "done"
    assert status_after("skipped", None) == "done"
    assert status_after("ended", {"id": "q2"}) == "done"
    assert status_after("judge_failed", {"id": "q2"}) == "awaiting_answer"
    assert status_after_plan([]) == "failed"
    assert status_after_plan([{"id": "q1"}]) == "awaiting_answer"


@pytest.fixture(autouse=True)
def _reset_budget():
    yield
    llm.configure_budget(None)
