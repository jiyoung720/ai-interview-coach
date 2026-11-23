"""추적 누출·장애 테스트 (M0 S5).

이 테스트가 증명하는 범위: **내보내기 직전 span(속성·이벤트·상태 설명)에서 표식이 검출되지 않았다.**
Langfuse 화면에서 세션이 묶여 보이는지는 키를 넣고 따로 확인한다(API 키 없이 도는 테스트가 아니므로).
"""
import pytest
from fastapi.testclient import TestClient
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from app.main import create_app
from core import llm
from core.config import load_settings
from core.llm import BudgetedEmbeddings, BudgetedModel
from core.tracing import AppTracer, TraceFieldError, configure_tracing
from rag.v2.turn_graph import SkeletonEngine

MARK = "MARK-7f3a9-원문"   # 이력서·답변·검색어·예외 메시지에 심는 고유 표식


def leaky_engine():
    """원문이 여기저기 흘러다니는 엔진. 이 중 어느 것도 추적으로 나가면 안 된다."""
    flaky = {"n": 0}

    class FlakyRunnable:
        def invoke(self, input, config=None, **kwargs):
            flaky["n"] += 1
            if flaky["n"] == 1:
                raise RuntimeError(f"외부 호출 실패: {input}")   # 예외 메시지에 원문
            return f"응답 {input}"

    class Embed:
        def embed_query(self, text):
            return [0.0]

        def embed_documents(self, texts):
            return [[0.0] for _ in texts]

    model = BudgetedModel(FlakyRunnable(), role="coach")
    embedder = BudgetedEmbeddings(Embed())

    def judge(question, answer):
        embedder.embed_query(f"검색어 {answer}")                # 검색어에 원문
        return {"diagnosis": "solid", "note": answer}

    def coach(question, judgement):
        return {"text": model.invoke(f"프롬프트 {judgement['note']}")}   # 프롬프트·응답에 원문

    def planner(request):
        return [{"id": "q1", "text": f"이력서 기반 질문 {request.get('sample_id')}", "depth": 0},
                {"id": "q2", "text": "질문 2", "depth": 0}]

    return SkeletonEngine(judge=judge, coach=coach, planner=planner)


def make_client(tmp_path, provider, engine=None):
    settings = load_settings({"APP_MODE": "demo", "SECRET_KEY": "s", "DATA_DIR": str(tmp_path)})
    app = create_app(settings, engine=engine or leaky_engine(), tracer_provider=provider, trace_strict=True)
    return TestClient(app, base_url="https://testserver", raise_server_exceptions=False)


def memory_provider():
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return provider, exporter


def run_session(client):
    session = client.post("/sessions", json={"sample_id": MARK}, headers={"Idempotency-Key": "c"}).json()
    for i, q in enumerate(["q1", "q2"]):
        current = client.get(f"/sessions/{session['session_id']}").json()
        client.post(
            f"/sessions/{session['session_id']}/events",
            json={"question_id": current["current_question"]["id"], "version": current["version"],
                  "answer": f"답변 {MARK} {i}"},
            headers={"Idempotency-Key": f"e{i}"},
        )
    return session


def exported_text(span) -> str:
    parts = [span.name, str(dict(span.attributes or {})), span.status.description or ""]
    for event in span.events:
        parts += [event.name, str(dict(event.attributes or {}))]
    return " ".join(parts)


def test_내보내기_직전_span에서_원문_표식이_검출되지_않는다(tmp_path):
    provider, exporter = memory_provider()
    with make_client(tmp_path, provider) as client:
        session = run_session(client)

    spans = exporter.get_finished_spans()
    assert {s.name for s in spans} >= {"plan", "session.event", "judge", "coach", "llm.call", "embedding", "commit"}
    for span in spans:
        text = exported_text(span)
        assert MARK not in text, span.name
        assert session["session_id"] not in text        # 앱 세션 ID도 내보내지 않는다
        assert not span.events                          # 자동 예외 기록(메시지·stack trace)이 없다

    # 외부 호출 실패는 메시지가 아니라 오류 코드(클래스 이름)로만 남는다
    failed = [s for s in spans if s.name == "llm.call" and s.attributes.get("app.error_code")]
    assert failed and failed[0].attributes["app.error_code"] == "RuntimeError"


def test_같은_세션의_요청들은_같은_추적_세션_ID로_묶인다(tmp_path):
    provider, exporter = memory_provider()
    with make_client(tmp_path, provider) as client:
        session = run_session(client)
    ids = {s.attributes["langfuse.session.id"] for s in exporter.get_finished_spans() if s.name == "session.event"}
    assert len(ids) == 1 and session["session_id"] not in ids


def test_추적_전송이_실패해도_면접은_진행된다(tmp_path):
    class BrokenExporter(SpanExporter):
        def export(self, spans):
            raise ConnectionError("Langfuse에 연결할 수 없음")

        def shutdown(self):
            pass

    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(BrokenExporter()))
    with make_client(tmp_path, provider, engine=SkeletonEngine()) as client:
        session = client.post("/sessions", json={}, headers={"Idempotency-Key": "c"})
        assert session.status_code == 200
        body = session.json()
        answered = client.post(
            f"/sessions/{body['session_id']}/events",
            json={"question_id": "q1", "version": body["version"], "answer": "답변"},
            headers={"Idempotency-Key": "e"},
        )
        assert answered.status_code == 200


def test_허용되지_않은_필드는_엄격_모드에서_예외_운영에서는_버린다():
    provider, exporter = memory_provider()
    with pytest.raises(TraceFieldError):
        with AppTracer(provider, strict=True).span("judge", answer="원문"):
            pass
    with AppTracer(provider, strict=False).span("judge", answer="원문", diagnosis="solid"):
        pass
    attrs = dict(exporter.get_finished_spans()[-1].attributes)
    assert attrs == {"app.diagnosis": "solid"}
    with pytest.raises(TraceFieldError):
        with AppTracer(provider).span("정의되지_않은_이름"):
            pass


@pytest.fixture(autouse=True)
def _reset():
    yield
    configure_tracing(None)
    llm.configure_budget(None)
