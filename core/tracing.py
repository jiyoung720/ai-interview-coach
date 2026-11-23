"""추적(관측성) 계층 (설계 §7.4-1).

앱 코드는 get_tracer().span(...)만 부른다. 이 계층이 두 가지를 강제한다.

1. **전송 허용 목록:** 고정된 span 이름과 허용된 필드만 보낸다. 원문(이력서·답변·검색어·프롬프트·
   응답 본문), 예외 메시지, 앱 세션 ID, owner_id, IP는 받지 않는다. 테스트에서는 위반 시 예외,
   운영에서는 조용히 버린다.
2. **자동 예외 기록 끔:** OpenTelemetry는 span 안에서 예외가 나면 메시지와 stack trace를 이벤트로
   붙이는데, 메시지에 원문이 섞일 수 있다. record_exception=False, set_status_on_exception=False로
   끄고, 예외는 클래스 이름만 고정 오류 코드로 남긴다.

전송은 OpenTelemetry OTLP로 Langfuse에 보낸다. 키가 없으면 내보내지 않는다(no-op).
전송 실패나 무료 한도 초과는 응답 경로를 막지 않는다(SDK가 내보내기 오류를 삼키고 로그만 남긴다).
LangChain 자동 계측은 프롬프트·응답을 통째로 보내므로 쓰지 않는다.
"""
import base64
import os
from contextlib import contextmanager

from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

SPAN_NAMES = frozenset({
    "session.create", "session.event", "session.replay",
    "state.load", "plan", "judge", "coach", "commit",
    "llm.call", "embedding", "retrieval", "rejudge", "hold",
})

# 필드 이름 → 내보낼 속성 키. 여기 없는 필드는 보내지 않는다.
ALLOWED_FIELDS = {
    "trace_session_id": "langfuse.session.id",   # 추적 전용 무작위 ID. 앱 세션 ID와 다르다
    "action": "app.action",
    "outcome": "app.outcome",
    "status": "app.status",
    "diagnosis": "app.diagnosis",
    "role": "llm.role",
    "model": "llm.model",
    "attempt": "llm.attempt",
    "tokens_in": "llm.tokens_in",
    "tokens_out": "llm.tokens_out",
    "kb_doc_ids": "app.kb_doc_ids",              # 공개 KB의 ID만. 사용자 문서 ID는 넣지 않는다
    "budget_exhausted": "app.budget_exhausted",
    "error_code": "app.error_code",
}


class TraceFieldError(ValueError):
    """허용되지 않은 span 이름이나 필드. 테스트에서만 올라간다."""


class AppTracer:
    def __init__(self, provider: TracerProvider | None, strict: bool = False):
        self._tracer = provider.get_tracer("ai-interview-coach") if provider else None
        self.strict = strict

    def _filter(self, name: str, fields: dict) -> dict:
        if name not in SPAN_NAMES:
            raise TraceFieldError(f"허용되지 않은 span 이름: {name}")
        return self._filter_fields(fields)

    def _filter_fields(self, fields: dict) -> dict:
        attributes = {}
        for key, value in fields.items():
            if key not in ALLOWED_FIELDS:
                if self.strict:
                    raise TraceFieldError(f"허용되지 않은 필드: {key}")
                continue
            if value is not None:
                attributes[ALLOWED_FIELDS[key]] = list(value) if isinstance(value, (list, tuple)) else value
        return attributes

    @contextmanager
    def span(self, name: str, **fields):
        attributes = self._filter(name, fields)   # 이름이 틀리면 strict가 아니어도 코드 버그라 알린다
        if self._tracer is None:
            yield _NoopSpan()
            return
        with self._tracer.start_as_current_span(
            name, attributes=attributes, record_exception=False, set_status_on_exception=False
        ) as otel_span:
            handle = _SpanHandle(otel_span, self)
            try:
                yield handle
            except BaseException as error:
                # 메시지는 버리고 클래스 이름만 남긴다
                otel_span.set_attribute(ALLOWED_FIELDS["error_code"], type(error).__name__)
                raise


class _SpanHandle:
    def __init__(self, otel_span, tracer: AppTracer):
        self._span = otel_span
        self._tracer = tracer

    def set(self, **fields) -> None:
        for key, value in self._tracer._filter_fields(fields).items():
            self._span.set_attribute(key, value)


class _NoopSpan:
    def set(self, **fields) -> None:
        pass


_tracer = AppTracer(None)


def get_tracer() -> AppTracer:
    return _tracer


def configure_tracing(provider: TracerProvider | None, strict: bool = False) -> AppTracer:
    global _tracer
    _tracer = AppTracer(provider, strict=strict)
    return _tracer


def langfuse_provider_from_env(env=os.environ) -> TracerProvider | None:
    """LANGFUSE_PUBLIC_KEY·LANGFUSE_SECRET_KEY가 있으면 Langfuse OTLP로 내보내는 provider를 만든다."""
    public_key, secret_key = env.get("LANGFUSE_PUBLIC_KEY"), env.get("LANGFUSE_SECRET_KEY")
    if not (public_key and secret_key):
        return None
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

    host = (env.get("LANGFUSE_HOST") or "https://cloud.langfuse.com").rstrip("/")
    token = base64.b64encode(f"{public_key}:{secret_key}".encode()).decode()
    exporter = OTLPSpanExporter(
        endpoint=f"{host}/api/public/otel/v1/traces",
        headers={"Authorization": f"Basic {token}"},
        timeout=5,
    )
    provider = TracerProvider(resource=Resource.create({"service.name": "ai-interview-coach"}))
    provider.add_span_processor(BatchSpanProcessor(exporter))   # 백그라운드 전송. 실패해도 요청은 계속된다
    return provider
