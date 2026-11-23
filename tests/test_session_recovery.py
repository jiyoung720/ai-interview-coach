"""세션 저장소와 복구 계약 (M0 S2).

v2는 체크포인터 없이 SQLite 하나에 상태를 둔다. 여기서는 "재시작해도 이어지는가",
"재전송해도 한 번만 반영되는가"를 가짜 엔진으로 LLM 없이 확인한다.
재시작은 SessionService를 새로 만들어(잠금·연결이 모두 새것) 흉내 낸다.
"""
import sqlite3
import threading

import pytest

from core.db import init_db
from core.session_service import Conflict, Expired, KeyReused, NotFound, SessionService
from rag.v2.turn_graph import SkeletonEngine

OWNER = "owner-a"


class Clock:
    def __init__(self, now=1_000_000.0):
        self.now = now

    def __call__(self):
        return self.now


@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "app.db"
    init_db(path)
    return path


def make_service(db_path, engine=None, clock=None):
    return SessionService(db_path, engine or SkeletonEngine(), clock=clock or Clock(), lock_timeout=5)


def answer(service, session, key, text, owner=OWNER):
    body = {"question_id": session["current_question"]["id"], "version": session["version"], "answer": text}
    return service.submit(owner, session["session_id"], key, body), body


def count(db_path, table):
    return sqlite3.connect(db_path).execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def test_재시작_후_같은_키_재전송은_저장된_응답이고_다음_질문으로_이어진다(db_path):
    service = make_service(db_path)
    session = service.create(OWNER, "create-1", {"sample_id": "s1"})
    assert session["status"] == "awaiting_answer"
    assert session["current_question"]["id"] == "q1"

    first, body = answer(service, session, "evt-1", "첫 답변")
    assert first["turn"]["seq"] == 1 and first["version"] == 2

    # 재시작: 프로세스 안의 잠금과 연결이 모두 사라진 상태
    restarted = make_service(db_path)
    replay = restarted.submit(OWNER, session["session_id"], "evt-1", body)
    assert replay == first                       # 같은 응답
    assert count(db_path, "turns") == 1          # 턴은 한 번만

    current = restarted.get(OWNER, session["session_id"])
    assert current["current_question"]["id"] == "q2"
    second, _ = answer(restarted, current, "evt-2", "두 번째 답변")
    assert second["status"] == "done" and second["next_question"] is None
    assert [t["seq"] for t in restarted.get(OWNER, session["session_id"])["turns"]] == [1, 2]


def test_꼬리질문도_재시작_후_이어진다(db_path):
    service = make_service(db_path)
    session = service.create(OWNER, "c", {})
    first, _ = answer(service, session, "e1", "잘 모름")
    assert first["next_question"]["id"] == "q1-f1"

    current = make_service(db_path).get(OWNER, session["session_id"])
    assert current["current_question"]["id"] == "q1-f1"   # 계획 목록에 없는 꼬리질문도 DB에 있다
    second, _ = answer(make_service(db_path), current, "e2", "이번엔 앎")
    assert second["next_question"]["id"] == "q2"


def test_커밋_전에_실패하면_아무_턴도_남지_않고_같은_키로_다시_처리된다(db_path):
    calls = {"n": 0}

    def flaky_judge(question, text):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("판정 중 장애")
        return {"diagnosis": "solid"}

    service = make_service(db_path, SkeletonEngine(judge=flaky_judge))
    session = service.create(OWNER, "c", {})
    with pytest.raises(RuntimeError):
        answer(service, session, "evt-1", "답변")
    assert count(db_path, "turns") == 0 and count(db_path, "idempotency") == 0
    assert service.get(OWNER, session["session_id"])["version"] == session["version"]

    retried, _ = answer(make_service(db_path, SkeletonEngine(judge=flaky_judge)), session, "evt-1", "답변")
    assert retried["turn"]["seq"] == 1


def test_같은_키에_다른_본문은_거부한다(db_path):
    service = make_service(db_path)
    session = service.create(OWNER, "c", {})
    answer(service, session, "evt-1", "답변 A")
    with pytest.raises(KeyReused):
        answer(service, session, "evt-1", "답변 B")


def test_오래된_버전이나_다른_질문에_대한_답은_충돌이다(db_path):
    service = make_service(db_path)
    session = service.create(OWNER, "c", {})
    answer(service, session, "evt-1", "답변")
    with pytest.raises(Conflict):
        answer(service, session, "evt-2", "옛 버전으로 보낸 답변")   # session은 이전 버전을 들고 있다


def test_남의_세션은_찾을_수_없다(db_path):
    service = make_service(db_path)
    session = service.create(OWNER, "c", {})
    with pytest.raises(NotFound):
        service.get("owner-b", session["session_id"])
    with pytest.raises(NotFound):
        answer(service, session, "evt", "답변", owner="owner-b")


def test_만료되면_410이고_정리되면_404다(db_path):
    clock = Clock()
    service = make_service(db_path, clock=clock)
    session = service.create(OWNER, "c", {})
    answer(service, session, "evt-1", "답변")

    clock.now += service.ttl + 1
    with pytest.raises(Expired):
        service.get(OWNER, session["session_id"])
    assert service.purge_expired() == 1
    with pytest.raises(NotFound):
        service.get(OWNER, session["session_id"])
    assert count(db_path, "turns") == 0 and count(db_path, "idempotency") == 0   # 연쇄 삭제


def test_계획_도중_실패한_세션은_같은_생성_키로_이어서_계획한다(db_path):
    attempts = {"n": 0}

    def flaky_planner(request):
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise RuntimeError("계획 중 장애")
        return [{"id": "q1", "text": "질문", "depth": 0}]

    with pytest.raises(RuntimeError):
        make_service(db_path, SkeletonEngine(planner=flaky_planner)).create(OWNER, "c", {"x": 1})
    session = make_service(db_path, SkeletonEngine(planner=flaky_planner)).create(OWNER, "c", {"x": 1})
    assert session["status"] == "awaiting_answer"
    assert count(db_path, "sessions") == 1       # 세션은 하나

    with pytest.raises(KeyReused):
        make_service(db_path).create(OWNER, "c", {"x": 2})


def test_진행_중인_요청과_삭제가_겹쳐도_삭제된_세션이_되살아나지_않는다(db_path):
    entered, release = threading.Event(), threading.Event()

    def slow_judge(question, text):
        entered.set()
        release.wait(5)
        return {"diagnosis": "solid"}

    service = make_service(db_path, SkeletonEngine(judge=slow_judge))
    session = service.create(OWNER, "c", {})
    results = {}

    def submit():
        try:
            results["answer"] = answer(service, session, "evt-1", "답변")[0]
        except Exception as e:   # noqa: BLE001
            results["error"] = e

    worker = threading.Thread(target=submit)
    worker.start()
    entered.wait(5)                                  # 판정 중(잠금을 쥔 상태)

    deleter = threading.Thread(target=lambda: service.delete(OWNER, session["session_id"]))
    deleter.start()
    release.set()                                    # 판정을 끝내게 한다
    worker.join(5)
    deleter.join(5)

    with pytest.raises(NotFound):
        service.get(OWNER, session["session_id"])
    assert count(db_path, "turns") == 0              # 먼저 커밋된 턴도 삭제와 함께 사라졌다
