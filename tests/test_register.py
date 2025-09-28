from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient) -> None:
    payload = {"username": "alice", "email": "alice@example.com", "password": "12345678"}
    resp1 = await client.post("/register", json=payload)
    assert resp1.status_code in (201, 409)
    if resp1.status_code == 201:
        data = resp1.json()
        assert data["username"] == "alice"
        assert data["email"] == "alice@example.com"
    else:
        # Retry with different unique user to avoid collision
        payload2 = {"username": "alice2", "email": "alice2@example.com", "password": "12345678"}
        resp2 = await client.post("/register", json=payload2)
        assert resp2.status_code == 201, resp2.text


@pytest.mark.asyncio
async def test_register_conflict_username(client: AsyncClient) -> None:
    payload = {"username": "bob", "email": "bob1@example.com", "password": "12345678"}
    resp = await client.post("/register", json=payload)
    assert resp.status_code in (201, 409)
    resp2 = await client.post("/register", json={"username": "bob", "email": "bob2@example.com", "password": "12345678"})
    assert resp2.status_code == 409


