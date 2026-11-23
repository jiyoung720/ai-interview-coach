"""외부 모델 계층: 모든 생성·임베딩 호출이 지나가는 한 곳 (설계 §7.4, §7.0).

모델 객체를 만드는 것과 호출하는 것을 분리했다. get_llm()이 돌려주는 래퍼는 **외부 호출을
시도할 때마다** 예산 게이트를 지난다. 구조화 출력이든 재시도든 경로가 달라도 우회할 수 없다.

- 재시도는 이 래퍼가 직접 한다(SDK 내부 재시도는 끈다). 그래야 시도마다 차감된다.
- 세션 서비스가 판정 1회분을 미리 예약했다면(reservation_scope), 첫 호출은 그 예약을 쓰고
  이중 차감하지 않는다.
- 게이트가 설정되지 않았으면(평가 스크립트 등) 차감하지 않는다. 앱은 기동 시 configure_budget()을 부른다.
"""
import contextvars
import os
from contextlib import contextmanager
from functools import lru_cache

from langchain_core.embeddings import Embeddings

from core.budget import BudgetExhausted, BudgetGate, Reservation
from core.tracing import get_tracer

DEFAULT_MAX_ATTEMPTS = 2          # 첫 시도 + 재시도 1회
DEFAULT_MAX_OUTPUT_TOKENS = 2048
DEFAULT_TIMEOUT_SECONDS = 60

_gate: BudgetGate | None = None
_reservation: contextvars.ContextVar[Reservation | None] = contextvars.ContextVar("llm_reservation", default=None)


def configure_budget(gate: BudgetGate | None) -> None:
    global _gate
    _gate = gate


def reserve_judgement() -> Reservation:
    """그래프를 실행하기 전에 판정 1회분을 예약한다. 예산이 없으면 BudgetExhausted.
    게이트가 없으면(스크립트·테스트) 차감 없이 빈 예약을 돌려준다."""
    if _gate is None:
        return Reservation()
    return _gate.reserve()


@contextmanager
def reservation_scope(reservation: Reservation):
    """이 블록 안의 첫 외부 호출이 예약분을 쓰게 한다."""
    token = _reservation.set(reservation)
    try:
        yield
    finally:
        _reservation.reset(token)


def charge() -> None:
    """외부 호출 1회분. 예약이 남아 있으면 그것을 쓰고, 아니면 게이트에서 차감한다."""
    reservation = _reservation.get()
    if reservation is not None and reservation.take():
        return
    if _gate is not None:
        _gate.consume()


class BudgetedModel:
    """LangChain 러너블을 감싸 호출 시도마다 charge()를 부르고, 시도마다 추적 span을 남긴다.
    span에는 역할·시도 번호·토큰 수만 남기고 프롬프트와 응답 본문은 남기지 않는다."""

    def __init__(self, runnable, max_attempts: int = DEFAULT_MAX_ATTEMPTS, role: str = "unknown"):
        self._runnable = runnable
        self._max_attempts = max_attempts
        self._role = role

    def with_structured_output(self, schema, **kwargs) -> "BudgetedModel":
        return BudgetedModel(self._runnable.with_structured_output(schema, **kwargs), self._max_attempts, self._role)

    def invoke(self, input, config=None, **kwargs):
        last_error = None
        for attempt in range(1, self._max_attempts + 1):
            with get_tracer().span("llm.call", role=self._role, attempt=attempt) as span:
                charge()                       # 예산이 없으면 여기서 BudgetExhausted가 올라간다
                try:
                    result = self._runnable.invoke(input, config, **kwargs)
                except BudgetExhausted:
                    raise
                except Exception as error:     # noqa: BLE001 - 외부 호출 실패는 재시도 대상
                    span.set(error_code=type(error).__name__)
                    last_error = error
                    continue
                usage = getattr(result, "usage_metadata", None) or {}
                span.set(tokens_in=usage.get("input_tokens"), tokens_out=usage.get("output_tokens"))
                return result
        raise last_error


class BudgetedEmbeddings(Embeddings):
    """임베딩 호출도 같은 게이트를 지난다. 호출 1번을 외부 요청 1회로 센다."""

    def __init__(self, inner: Embeddings):
        self._inner = inner

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        with get_tracer().span("embedding"):
            charge()
            return self._inner.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        with get_tracer().span("embedding"):
            charge()
            return self._inner.embed_query(text)


def _model_name(role: str) -> str:
    # 역할별로 모델을 바꿀 수 있다 (예: LLM_MODEL_EVAL_JUDGE). 없으면 GEMINI_MODEL.
    return os.getenv(f"LLM_MODEL_{role.upper()}") or os.getenv("GEMINI_MODEL", "gemini-3.5-flash")


@lru_cache(maxsize=None)
def get_llm(role: str) -> BudgetedModel:
    from langchain_google_genai import ChatGoogleGenerativeAI

    model = ChatGoogleGenerativeAI(
        model=_model_name(role),
        max_retries=0,                                  # 재시도는 BudgetedModel이 시도마다 차감하며 한다
        timeout=DEFAULT_TIMEOUT_SECONDS,
        max_output_tokens=DEFAULT_MAX_OUTPUT_TOKENS,
    )
    return BudgetedModel(model, role=role)


def get_embedder(inner: Embeddings) -> BudgetedEmbeddings:
    return BudgetedEmbeddings(inner)
