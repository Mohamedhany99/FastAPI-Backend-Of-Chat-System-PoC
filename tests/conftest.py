from __future__ import annotations

import asyncio
import os
from typing import AsyncIterator, Iterator, Any

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from httpx import AsyncClient
from httpx import ASGITransport
from asgi_lifespan import LifespanManager

import app.db as app_db
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.deps import get_redis
from app.routers import auth, messages


# Force test DB to in-memory before any app.* modules consult settings
os.environ["DATABASE_URL_ENV"] = "sqlite+aiosqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret"
DATABASE_URL_ENV = os.environ["DATABASE_URL_ENV"]

@pytest.fixture(scope="session")
def event_loop() -> Iterator[asyncio.AbstractEventLoop]:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# @pytest.fixture(scope="session")
# def test_env() -> dict[str, str]:
#     # Set env before app imports read settings
#     _os.environ["DATABASE_URL_ENV"] = "sqlite+aiosqlite:///:memory:"
#     _os.environ["SECRET_KEY"] = "test-secret"
#     return dict(_os.environ)


@pytest_asyncio.fixture()
async def app() -> AsyncIterator[FastAPI]:
    # Create shared in-memory engine and session factory for tests
    engine = create_async_engine(
        DATABASE_URL_ENV,
        echo=False,
        pool_pre_ping=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    # Ensure tables exist before app starts
    async with engine.begin() as conn:
        await conn.run_sync(app_db.Base.metadata.create_all)

    application = FastAPI(title="Test Chat Service")
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(auth.router)
    application.include_router(messages.router)

    # Override DB dependency to use test session
    async def _get_db() -> AsyncIterator[AsyncSession]:
        async with AsyncSessionLocal() as session:
            yield session

    application.dependency_overrides[app_db.get_db] = _get_db

    # Fake Redis for tests
    class FakeRedis:
        def __init__(self) -> None:
            self.store: dict[str, str] = {}

        async def get(self, key: str) -> Any:
            return self.store.get(key)

        async def set(self, key: str, value: str, ex: int | None = None) -> None:  # noqa: ARG002
            self.store[key] = value

        async def incr(self, key: str) -> int:
            val = int(self.store.get(key, "0")) + 1
            self.store[key] = str(val)
            return val

        async def close(self) -> None:
            return None

    async def override_get_redis() -> AsyncIterator[FakeRedis]:
        client = FakeRedis()
        try:
            yield client
        finally:
            await client.close()

    application.dependency_overrides[get_redis] = override_get_redis
    yield application
    application.dependency_overrides.clear()


@pytest_asyncio.fixture()
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


