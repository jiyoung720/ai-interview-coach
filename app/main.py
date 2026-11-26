"""FastAPI 진입점.

모드에 따라 등록하는 라우터가 다르다 (설계 §2.5, §8).
- demo : 공개 서버. 공통 라우터만. 업로드와 v1 엔드포인트는 아예 등록하지 않는다.
- local: 제작자 노트북. v1 라우터까지 등록한다. v1 코드는 M2에서 v2로 교체될 때 지운다.

uvicorn은 `app.main:app`을 그대로 쓰면 된다. 모듈 속성 `app`을 처음 읽을 때
환경변수로 설정을 만들어 앱을 생성한다(아래 __getattr__). 테스트는 create_app()에
설정과 엔진을 직접 넘긴다.
"""
import asyncio
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from api.sessions import router as sessions_router
from core.budget import BudgetExhausted, BudgetGate
from core.config import Settings, load_settings
from core.db import init_db
from core.llm import configure_budget
from core.locks import LockTimeout
from core.owner import OwnerMiddleware
from core.session_service import ServiceError, SessionService, VisitorLimits
from core.tracing import configure_tracing, langfuse_provider_from_env

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
PURGE_INTERVAL_SECONDS = 60 * 60
# 로컬 모드는 SECRET_KEY 없이도 뜬다. 쿠키 서명이 재시작 후에도 유지되도록 고정값을 쓴다(노트북 전용).
LOCAL_FALLBACK_SECRET = "local-only-not-for-public-servers"


def create_app(settings: Settings | None = None, engine=None, tracer_provider=None, trace_strict: bool = False) -> FastAPI:
    settings = settings or load_settings()
    if engine is None:
        from rag.v2.turn_graph import SkeletonEngine   # M0: 가짜 판정 골격. M2에서 진짜 엔진으로 교체

        engine = SkeletonEngine()

    service = SessionService(
        settings.db_path,
        engine,
        visitor_limits=VisitorLimits() if settings.is_demo else None,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        init_db(settings.db_path)
        # 모든 외부 모델 호출이 이 게이트를 지난다 (core/llm.py)
        configure_budget(BudgetGate(settings.db_path, settings.daily_llm_budget))
        # Langfuse 키가 없으면 내보내지 않는다. 테스트는 tracer_provider로 메모리 exporter를 넘긴다
        provider = tracer_provider if tracer_provider is not None else langfuse_provider_from_env()
        configure_tracing(provider, strict=trace_strict)
        purge_task = asyncio.create_task(_purge_loop(service))
        yield
        purge_task.cancel()
        with suppress(asyncio.CancelledError):
            await purge_task
        if provider is not None and tracer_provider is None:
            provider.shutdown()
        configure_tracing(None)
        configure_budget(None)

    app = FastAPI(title="AI Interview Coach", lifespan=lifespan)
    app.state.settings = settings
    app.state.session_service = service
    app.add_middleware(
        OwnerMiddleware,
        secret=settings.secret_key or LOCAL_FALLBACK_SECRET,
        secure=settings.is_demo,
    )
    _register_error_handlers(app)

    @app.get("/health")
    def health_check():
        return {"status": "ok", "mode": settings.app_mode}

    app.include_router(sessions_router)

    if settings.is_local:
        _register_v1(app)
    else:
        @app.get("/")
        def index_demo():
            # v2 데모 화면은 M2에서 붙는다. 그 전까지 공개 서버는 상태만 알린다.
            return JSONResponse({"status": "ok", "message": "v2 데모 준비 중입니다."})

    return app


async def _purge_loop(service: SessionService) -> None:
    """기동 직후 한 번, 이후 1시간마다 만료 세션을 지운다."""
    while True:
        await asyncio.to_thread(service.purge_expired)
        await asyncio.sleep(PURGE_INTERVAL_SECONDS)


def _register_error_handlers(app: FastAPI) -> None:
    def error(status: int, message: str) -> JSONResponse:
        return JSONResponse(status_code=status, content={"detail": message})

    @app.exception_handler(ServiceError)
    async def on_service_error(request: Request, exc: ServiceError):
        return error(exc.status_code, str(exc))

    @app.exception_handler(BudgetExhausted)
    async def on_budget(request: Request, exc: BudgetExhausted):
        return error(429, "오늘 체험 한도에 도달했습니다.")

    @app.exception_handler(LockTimeout)
    async def on_lock_timeout(request: Request, exc: LockTimeout):
        # 같은 세션의 다른 요청이 처리 중이다. 클라이언트는 같은 키로 다시 보내면 된다.
        return error(409, "같은 세션의 요청을 처리하고 있습니다. 잠시 후 다시 시도해 주세요.")


def _register_v1(app: FastAPI) -> None:
    """v1 라우터와 화면. 무거운 rag 모듈을 데모 모드에서 import하지 않도록 여기서만 불러온다."""
    from api.documents import router as documents_router
    from api.evaluations import router as evaluations_router
    from api.interviews import router as interviews_router
    from api.questions import router as questions_router

    app.include_router(documents_router)
    app.include_router(questions_router)
    app.include_router(evaluations_router)
    app.include_router(interviews_router)
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    # M1 B5 라벨링 화면. 레포의 eval_v2/labels에 판정을 저장하므로 제작자 노트북에서만 연다.
    from api.labeling import create_labeling_router

    app.include_router(create_labeling_router(Path(__file__).resolve().parent.parent))

    @app.get("/")
    def index():
        return FileResponse(STATIC_DIR / "index.html")


_app: FastAPI | None = None


def __getattr__(name: str):
    # `uvicorn app.main:app`이 속성을 읽는 순간에만 설정을 검증하고 앱을 만든다.
    # import만으로 기동 검증이 돌면 설정 없는 테스트·스크립트가 깨지기 때문이다.
    global _app
    if name == "app":
        if _app is None:
            _app = create_app()
        return _app
    raise AttributeError(name)
