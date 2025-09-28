from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..deps import get_redis
from ..schemas import LoginRequest, TokenResponse, UserCreate, UserPublic
from ..services import AuthService


router = APIRouter(tags=["auth"])


def _bucket_key(ip: str) -> str:
    return f"rl:login:{ip}"


@router.post("/register", response_model=UserPublic, status_code=201)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)) -> Any:
    svc = AuthService(db)
    try:
        user = await svc.register(payload.username, payload.email, payload.password)
    except ValueError as e:
        if str(e) == "username_taken":
            raise HTTPException(status_code=409, detail="Username already exists")
        if str(e) == "email_taken":
            raise HTTPException(status_code=409, detail="Email already exists")
        raise
    return UserPublic.model_validate(user.__dict__)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: Any = Depends(get_redis),
) -> Any:
    # Simple fixed-window rate limit per IP
    ip = request.client.host if request.client else "unknown"
    key = _bucket_key(ip)
    current = await redis.get(key)
    if current is None:
        await redis.set(key, "1", ex=60)
    else:
        count = int(current)
        if count >= 5:
            raise HTTPException(status_code=429, detail="Too many login attempts, try later")
        await redis.incr(key)

    svc = AuthService(db)
    try:
        token, expires_in, user = await svc.login(payload.username, payload.password)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return TokenResponse(access_token=token, expires_in=expires_in)
