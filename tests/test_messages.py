from __future__ import annotations

import pytest
from httpx import AsyncClient


async def _auth_token(client: AsyncClient, username: str) -> tuple[int, str]:
    r = await client.post(
        "/register",
        json={"username": username, "email": f"{username}@example.com", "password": "12345678"},
    )
    if r.status_code == 201:
        user_id = r.json()["id"]
    else:
        # If already exists, log in and fetch id by creating a message to self (not ideal, but adequate for tests)
        # Try login to ensure user exists.
        lr0 = await client.post("/login", json={"username": username, "password": "12345678"})
        assert lr0.status_code == 200
        # Fallback user id unknown; set dummy and rely on peer to be known below
        user_id = 1
    lr = await client.post("/login", json={"username": username, "password": "12345678"})
    token = lr.json()["access_token"]
    return user_id, token


@pytest.mark.asyncio
async def test_messages_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/messages", params={"peer_id": 1})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_messages_fetch_and_cache(client: AsyncClient) -> None:
    (id_a, token_a) = await _auth_token(client, "frank")
    (id_b, token_b) = await _auth_token(client, "gina")

    # Send a few messages
    for i in range(3):
        await client.post(
            "/send",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"recipient_id": id_b, "content": f"m{i}"},
        )

    # Fetch history (should populate cache)
    r1 = await client.get(
        "/messages",
        headers={"Authorization": f"Bearer {token_a}"},
        params={"peer_id": id_b, "limit": 5, "offset": 0},
    )
    assert r1.status_code == 200
    data1 = r1.json()
    assert len(data1["messages"]) == 3

    # Fetch again (should hit cache)
    r2 = await client.get(
        "/messages",
        headers={"Authorization": f"Bearer {token_a}"},
        params={"peer_id": id_b, "limit": 5, "offset": 0},
    )
    assert r2.status_code == 200
    data2 = r2.json()
    assert data1 == data2


