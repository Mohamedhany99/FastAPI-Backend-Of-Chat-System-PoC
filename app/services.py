from __future__ import annotations

from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from .repositories import UserRepository, MessageRepository
from .security import hash_password, verify_password, create_access_token
from .models import User, Message


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.users = UserRepository(db)

    async def register(self, username: str, email: str, password: str) -> User:
        if await self.users.get_by_username(username):
            raise ValueError("username_taken")
        if await self.users.get_by_email(email):
            raise ValueError("email_taken")
        return await self.users.create(
            username=username, email=email, password_hash=hash_password(password)
        )

    async def login(self, username: str, password: str) -> tuple[str, int, User]:
        user = await self.users.get_by_username(username)
        if not user or not verify_password(password, user.password_hash):
            raise ValueError("invalid_credentials")
        token, expires_in = create_access_token(str(user.id))
        return token, expires_in, user


class MessagingService:
    def __init__(self, db: AsyncSession) -> None:
        self.messages = MessageRepository(db)

    async def send(self, sender_id: int, recipient_id: int, content: str) -> Message:
        return await self.messages.create(sender_id, recipient_id, content)

    async def history(
        self, user_id: int, peer_id: int, limit: int, offset: int
    ) -> Sequence[Message]:
        return await self.messages.history(user_id, peer_id, limit, offset)

    async def count_history(self, user_id: int, peer_id: int) -> int:
        return await self.messages.count_history(user_id, peer_id)
