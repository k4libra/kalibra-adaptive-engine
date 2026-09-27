from fastapi import FastAPI

from kalibra_engine.shared.infrastructure.lifespan import lifespan
from kalibra_engine.shared.interfaces.rest.engine_exception_handler import EngineExceptionHandler
from kalibra_engine.shared.interfaces.rest.health_router import router as health_router


def create_app() -> FastAPI:
    """Compose the Kalibra Adaptive Engine application.

    Returns:
        The configured FastAPI application.
    """
    app = FastAPI(
        title="Kalibra Adaptive Engine",
        summary="Mastery estimation, exercise generation and verification for Kalibra.",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.include_router(health_router)
    EngineExceptionHandler(status_by_exception={}).register(app)
    return app


app = create_app()
