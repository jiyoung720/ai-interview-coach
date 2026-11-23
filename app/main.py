"""FastAPI 진입점.

모드에 따라 등록하는 라우터가 다르다 (설계 §2.5, §8).
- demo : 공개 서버. 공통 라우터만. 업로드와 v1 엔드포인트는 아예 등록하지 않는다.
- local: 제작자 노트북. v1 라우터까지 등록한다. v1 코드는 M2에서 v2로 교체될 때 지운다.

uvicorn은 `app.main:app`을 그대로 쓰면 된다. 모듈 속성 `app`을 처음 읽을 때
환경변수로 설정을 만들어 앱을 생성한다(아래 __getattr__). 테스트는 create_app()에
설정을 직접 넘긴다.
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from core.budget import BudgetGate
from core.config import Settings, load_settings
from core.db import init_db
from core.llm import configure_budget

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        init_db(settings.db_path)
        # 모든 외부 모델 호출이 이 게이트를 지난다 (core/llm.py)
        configure_budget(BudgetGate(settings.db_path, settings.daily_llm_budget))
        yield
        configure_budget(None)

    app = FastAPI(title="AI Interview Coach", lifespan=lifespan)
    app.state.settings = settings

    @app.get("/health")
    def health_check():
        return {"status": "ok", "mode": settings.app_mode}

    if settings.is_local:
        _register_v1(app)
    else:
        @app.get("/")
        def index_demo():
            # v2 데모 화면은 M2에서 붙는다. 그 전까지 공개 서버는 상태만 알린다.
            return JSONResponse({"status": "ok", "message": "v2 데모 준비 중입니다."})

    return app


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
