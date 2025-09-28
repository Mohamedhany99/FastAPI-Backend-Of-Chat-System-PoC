from __future__ import annotations

from datetime import datetime, timezone
from typing import AsyncIterator, Any

from fastapi import Depends, HTTPException, Request, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from .db import get_db
from .models import User
from .security import decode_access_token
from .settings import get_settings


async def get_redis() -> AsyncIterator[Any]:
    from redis.asyncio import from_url

    settings = get_settings()
    client: Any = from_url(settings.redis_url, decode_responses=True)
    try:
        yield client
    finally:
        await client.close()


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    auth = request.headers.get("Authorization")
    if not auth or not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    token = auth.split(" ", 1)[1]
    try:
        payload = decode_access_token(token)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    stmt = select(User).where(User.id == int(sub))
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    # Update last_active
    await db.execute(
        update(User).where(User.id == user.id).values(last_active=datetime.now(timezone.utc))
    )
    await db.commit()
    return user
