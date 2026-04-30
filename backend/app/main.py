from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as v1_router
from app.config import settings
from app.errors import register_exception_handlers
from app.middleware.correlation import CORRELATION_HEADER, CorrelationIDMiddleware


def create_app() -> FastAPI:
    app = FastAPI(title="PREDICT Event API", version="0.1.0")

    # Starlette runs the LAST-registered middleware as the OUTERMOST layer.
    # CORSMiddleware short-circuits OPTIONS preflight, so it must be inner —
    # otherwise the correlation ID never gets stamped on preflight responses.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[CORRELATION_HEADER],
    )
    app.add_middleware(CorrelationIDMiddleware)

    register_exception_handlers(app)
    app.include_router(v1_router)
    return app


app = create_app()
