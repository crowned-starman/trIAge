# backend/tests/test_queue.py

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock
from app.main import app


# Fixtures

@pytest.fixture
def mock_queue():
    return [
        _fake_queue_entry(priority=1, position=1, status="waiting"),
        _fake_queue_entry(priority=2, position=2, status="waiting"),
        _fake_queue_entry(priority=3, position=3, status="in_progress"),
    ]


# GET /queue

@pytest.mark.asyncio
async def test_get_queue_returns_200(mock_queue):
    with patch("app.db.crud.get_queue", new_callable=AsyncMock, return_value=mock_queue):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/queue")

    assert response.status_code == 200
    assert len(response.json()) == 3


@pytest.mark.asyncio
async def test_queue_sorted_by_priority(mock_queue):
    with patch("app.db.crud.get_queue", new_callable=AsyncMock, return_value=mock_queue):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/queue")

    priorities = [e["priority"] for e in response.json()]
    assert priorities == sorted(priorities)


@pytest.mark.asyncio
async def test_get_queue_invalid_status_returns_422():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/queue?status=invalid")

    assert response.status_code == 422


# PATCH /queue/{patient_id}

@pytest.mark.asyncio
async def test_update_status_valid_transition():
    entry = _fake_queue_entry(status="waiting")

    with patch("app.db.crud.get_queue_entry",   new_callable=AsyncMock, return_value=entry), \
         patch("app.db.crud.update_queue_status", new_callable=AsyncMock,
               return_value=_fake_queue_entry(status="in_progress")):

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.patch(
                f"/api/v1/queue/{entry.patient_id}",
                json={"status": "in_progress"}
            )

    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"


@pytest.mark.asyncio
async def test_update_status_invalid_transition():
    entry = _fake_queue_entry(status="waiting")

    with patch("app.db.crud.get_queue_entry", new_callable=AsyncMock, return_value=entry):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.patch(
                f"/api/v1/queue/{entry.patient_id}",
                json={"status": "done"}  # waiting -> done no permitido
            )

    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_STATUS_TRANSITION"


@pytest.mark.asyncio
async def test_get_queue_entry_not_found():
    with patch("app.db.crud.get_queue_entry", new_callable=AsyncMock, return_value=None):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/queue/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404
    assert response.json()["code"] == "QUEUE_ENTRY_NOT_FOUND"
