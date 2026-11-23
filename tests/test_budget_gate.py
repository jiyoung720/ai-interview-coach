"""예산 게이트 (M0 S3).

공개 데모의 비용 차단이 실제 외부 호출 단위로 동작하는지 API 키 없이 확인한다.
외부 모델은 호출 횟수만 세는 가짜 러너블로 대신한다.
"""
import threading

import pytest

from core import llm
from core.budget import BudgetExhausted, BudgetGate
from core.db import init_db
from core.llm import BudgetedEmbeddings, BudgetedModel, reservation_scope


class FakeRunnable:
    def __init__(self, fail_times=0):
        self.calls = 0
        self.fail_times = fail_times

    def invoke(self, input, config=None, **kwargs):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise RuntimeError("일시 장애")
        return f"응답:{input}"

    def with_structured_output(self, schema, **kwargs):
        return self   # 구조화 출력도 결국 같은 외부 호출


class FakeEmbeddings:
    def embed_documents(self, texts):
        return [[0.0] for _ in texts]

    def embed_query(self, text):
        return [0.0]


@pytest.fixture
def gate(tmp_path):
    path = tmp_path / "app.db"
    init_db(path)
    gate = BudgetGate(path, daily_limit=5, clock=lambda: 1_700_000_000.0)
    llm.configure_budget(gate)
    yield gate
    llm.configure_budget(None)


def test_호출마다_차감하고_한도에서_막힌다(gate):
    model = BudgetedModel(FakeRunnable())
    for _ in range(5):
        model.invoke("q")
    assert gate.used_today() == 5
    with pytest.raises(BudgetExhausted):
        model.invoke("q")


def test_재시도도_시도마다_차감한다(gate):
    runnable = FakeRunnable(fail_times=1)
    assert BudgetedModel(runnable, max_attempts=2).invoke("q") == "응답:q"
    assert runnable.calls == 2 and gate.used_today() == 2


def test_구조화_출력_경로도_게이트를_지난다(gate):
    BudgetedModel(FakeRunnable()).with_structured_output(dict).invoke("q")
    assert gate.used_today() == 1


def test_임베딩도_차감한다(gate):
    embedder = BudgetedEmbeddings(FakeEmbeddings())
    embedder.embed_query("q")
    embedder.embed_documents(["a", "b"])
    assert gate.used_today() == 2


def test_예약분은_첫_호출이_한_번만_쓴다(gate):
    reservation = gate.reserve()               # 그래프 실행 전에 판정 1회분 차감
    assert gate.used_today() == 1
    model = BudgetedModel(FakeRunnable())
    with reservation_scope(reservation):
        model.invoke("판정")                    # 예약분 사용, 추가 차감 없음
        assert gate.used_today() == 1
        model.invoke("코칭")                    # 그다음 호출은 차감
    assert gate.used_today() == 2


def test_동시에_몰려도_상한을_넘지_않는다(gate):
    errors = []

    def worker():
        try:
            gate.consume()
        except BudgetExhausted as e:
            errors.append(e)

    threads = [threading.Thread(target=worker) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert gate.used_today() == 5 and len(errors) == 15


def test_재시작해도_오늘_쓴_양이_유지된다(gate):
    gate.consume()
    gate.consume()
    restarted = BudgetGate(gate.db_path, daily_limit=5, clock=gate.clock)
    assert restarted.used_today() == 2


def test_한국_시간_자정에_초기화된다(tmp_path):
    path = tmp_path / "app.db"
    init_db(path)
    now = {"t": 1_700_000_000.0}
    gate = BudgetGate(path, daily_limit=1, clock=lambda: now["t"])
    gate.consume()
    with pytest.raises(BudgetExhausted):
        gate.consume()
    now["t"] += 24 * 60 * 60                    # 다음 날
    gate.consume()
