from __future__ import annotations

import pytest
from httpx import AsyncClient


async def _auth_token(client: AsyncClient, username: str) -> str:
    await client.post("/register", json={"username": username, "email": f"{username}@example.com", "password": "12345678"})
    resp = await client.post("/login", json={"username": username, "password": "12345678"})
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_send_requires_auth(client: AsyncClient) -> None:
    resp = await client.post("/send", json={"recipient_id": 1, "content": "hi"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_send_success(client: AsyncClient) -> None:
    await client.post("/register", json={"username": "dave", "email": "dave@example.com", "password": "12345678"})
    await client.post("/register", json={"username": "erin", "email": "erin@example.com", "password": "12345678"})
    resp_a = await client.post("/login", json={"username": "dave", "password": "12345678"})
    token_a = resp_a.json()["access_token"]
    # Fetch erin id via messages precondition not available; assume IDs are sequential (2 for erin)

    # Send from dave to erin
    resp = await client.post(
        "/send",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"recipient_id": 2, "content": "hello"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["sender_id"] > 0 and body["recipient_id"] > 0
    assert body["content"] == "hello"


