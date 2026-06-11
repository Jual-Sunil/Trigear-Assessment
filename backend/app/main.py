"""FastAPI application factory and ASGI entrypoint."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from api.router import api_router
from core.config import get_settings
from core.logging import configure_logging, get_logger
from infrastructure.database.session import dispose_engine, get_engine

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown lifecycle.

    Initialises the database engine on startup, pre-loads the zero-shot
    classification model so the first sync avoids a multi-minute cold
    start, and disposes resources cleanly on shutdown.

    Args:
        app: The FastAPI application instance.

    Yields:
        Control to the ASGI server while the application is running.
    """
    settings = get_settings()
    logger.info(
        "application_starting",
        environment=settings.environment,
        version=settings.app_version,
    )

    # Eagerly validate the database connection pool on startup.
    get_engine()
    logger.info("database_pool_initialized")

    # Pre-load the BART zero-shot classification model in a background
    # thread so the first sync request doesn't block for ~2 minutes.
    import asyncio

    from infrastructure.ai.classification.zero_shot_classifier import ZeroShotClassifier

    classifier = ZeroShotClassifier()
    await asyncio.to_thread(classifier.load)
    logger.info("classification_model_preloaded")

    yield

    logger.info("application_shutting_down")
    await dispose_engine()
    logger.info("application_stopped")


def create_app() -> FastAPI:
    """Construct and configure the FastAPI application.

    Registers middleware, routers, and event handlers.

    Returns:
        A fully configured :class:`FastAPI` instance ready for serving.
    """
    configure_logging()
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # ------------------------------------------------------------------
    # Middleware
    # ------------------------------------------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    if settings.is_production:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["*"],  # Tighten per deployment environment.
        )

    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.get("/health", tags=["Health"])
    async def health_check() -> dict[str, str]:
        """Return application health status.

        Returns:
            A dictionary with a ``status`` key set to ``"ok"``.
        """
        return {"status": "ok", "version": settings.app_version}

    return app


app: FastAPI = create_app()
