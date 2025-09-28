from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..cache import get_conversation_cache, push_conversation_cache, set_conversation_cache
from ..deps import get_current_user, get_redis
from ..db import get_db
from ..models import User
from ..schemas import MessageResponse, MessageSendRequest, MessagesPage
from ..services import MessagingService


router = APIRouter(tags=["messages"])


def _rl_key(user_id: int) -> str:
    return f"rl:send:{user_id}"


@router.post("/send", response_model=MessageResponse)
async def send(
    payload: MessageSendRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: Any = Depends(get_redis),
    user: User = Depends(get_current_user),
) -> Any:
    # Rate limit per user: 30 per minute
    key = _rl_key(user.id)
    current = await redis.get(key)
    if current is None:
        await redis.set(key, "1", ex=60)
    else:
        if int(current) >= 30:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        await redis.incr(key)

    svc = MessagingService(db)
    msg = await svc.send(
        sender_id=user.id, recipient_id=payload.recipient_id, content=payload.content
    )

    resp = MessageResponse(
        id=msg.id,
        sender_id=msg.sender_id,
        recipient_id=msg.recipient_id,
        content=msg.content,
        created_at=msg.created_at,
    )

    await push_conversation_cache(
        redis, user.id, payload.recipient_id, resp.model_dump(mode="json")
    )
    return resp


@router.get("/messages", response_model=MessagesPage)
async def messages(
    peer_id: int = Query(..., description="Peer user id"),
    limit: int = Query(5, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    redis: Any = Depends(get_redis),
    user: User = Depends(get_current_user),
) -> Any:
    # Try cache first
    cached = await get_conversation_cache(redis, user.id, peer_id, limit, offset)
    if cached is not None and offset == 0:
        parsed = [MessageResponse(**m) for m in cached]
        return MessagesPage(messages=parsed, limit=limit, offset=offset)

    svc = MessagingService(db)
    msgs = await svc.history(user.id, peer_id, limit, offset)
    resp: list[MessageResponse] = [
        MessageResponse(
            id=m.id,
            sender_id=m.sender_id,
            recipient_id=m.recipient_id,
            content=m.content,
            created_at=m.created_at,
        )
        for m in msgs
    ]
    if offset == 0:
        await set_conversation_cache(
            redis, user.id, peer_id, [r.model_dump(mode="json") for r in resp]
        )
    total = await svc.count_history(user.id, peer_id)
    return MessagesPage(messages=resp, limit=limit, offset=offset, total=total)
