from __future__ import annotations

import logging
import time
import uuid
from contextvars import ContextVar
from typing import AsyncIterator, Callable, Awaitable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from .settings import Settings, get_settings
from .db import async_engine, Base
from .routers import auth, messages


request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


def _setup_logging() -> None:
    """Configure plain-text logging including correlation/request ID."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s request_id=%(request_id)s %(name)s: %(message)s",
    )

    # Inject request_id into log records
    class RequestIDFilter(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:  # noqa: D401
            record.request_id = request_id_ctx.get()
            return True

    for handler in logging.getLogger().handlers:
        handler.addFilter(RequestIDFilter())


_setup_logging()
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: create database tables on startup as requested."""
    logger.info("Starting up, creating database tables if not exist")
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    logger.info("Shutting down")


def create_app(settings: Settings | None = None) -> FastAPI:
    # Use provided settings (e.g., tests) or global settings
    settings = settings or get_settings()

    app = FastAPI(
        title="Chat Service",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def add_request_id(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        rid = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request_id_ctx.set(rid)
        start = time.perf_counter()
        response: Response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Request-ID"] = rid
        logger.info(
            "%s %s %s %.2fms", request.method, request.url.path, response.status_code, duration_ms
        )
        return response

    # Routers
    app.include_router(auth.router, prefix="")
    app.include_router(messages.router, prefix="")

    @app.get("/health")
    async def check_health() -> dict[str, str]:
        return {"status": "ok"}

    return app


def run() -> None:
    """Entrypoint for `poetry run chat-service`. Uvicorn should be used in Docker."""
    import uvicorn

    uvicorn.run("app.main:create_app", factory=True, host="0.0.0.0", port=8000, reload=False)
