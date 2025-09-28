from __future__ import annotations

from typing import Sequence

from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from .models import User, Message


class UserRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_username(self, username: str) -> User | None:
        res = await self.db.execute(select(User).where(User.username == username))
        return res.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        res = await self.db.execute(select(User).where(User.email == email))
        return res.scalar_one_or_none()

    async def create(self, username: str, email: str, password_hash: str) -> User:
        user = User(username=username, email=email, password_hash=password_hash)
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        await self.db.commit()
        return user


class MessageRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, sender_id: int, recipient_id: int, content: str) -> Message:
        msg = Message(sender_id=sender_id, recipient_id=recipient_id, content=content)
        self.db.add(msg)
        await self.db.flush()
        await self.db.refresh(msg)
        await self.db.commit()
        return msg

    async def history(
        self, user_id: int, peer_id: int, limit: int, offset: int
    ) -> Sequence[Message]:
        stmt = (
            select(Message)
            .where(
                ((Message.sender_id == user_id) & (Message.recipient_id == peer_id))
                | ((Message.sender_id == peer_id) & (Message.recipient_id == user_id))
            )
            .order_by(desc(Message.created_at))
            .limit(limit)
            .offset(offset)
        )
        res = await self.db.execute(stmt)
        return res.scalars().all()

    async def count_history(self, user_id: int, peer_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(Message)
            .where(
                ((Message.sender_id == user_id) & (Message.recipient_id == peer_id))
                | ((Message.sender_id == peer_id) & (Message.recipient_id == user_id))
            )
        )
        res = await self.db.execute(stmt)
        return int(res.scalar_one())
