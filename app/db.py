from __future__ import annotations

from typing import AsyncIterator

from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine, create_async_engine

from .settings import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
async_engine: AsyncEngine = create_async_engine(
    settings.database_url, echo=False, pool_pre_ping=True
)
AsyncSessionLocal = sessionmaker(  # type: ignore[call-overload]
    bind=async_engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db() -> AsyncIterator[AsyncSession]:
    """Yield an async DB session."""
    async with AsyncSessionLocal() as session:
        yield session
