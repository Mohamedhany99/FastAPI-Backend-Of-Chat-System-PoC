from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient) -> None:
    await client.post("/register", json={"username": "charlie", "email": "charlie@example.com", "password": "12345678"})
    resp = await client.post("/login", json={"username": "charlie", "password": "12345678"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["token_type"] == "bearer"
    assert "access_token" in data


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient) -> None:
    resp = await client.post("/login", json={"username": "ghost", "password": "nope"})
    assert resp.status_code == 401


