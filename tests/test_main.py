# tests/test_main.py

import asyncio
from datetime import datetime, timezone

# Catatan: Fixture 'client' otomatis di-inject dari conftest.py

async def test_get_stats_initial(client):
    """Tes status awal (harus 0 semua)."""
    response = await client.get("/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["received_events"] == 0
    assert data["unique_events"] == 0
    assert data["duplicates"] == 0

async def test_publish_single_event(client):
    """Tes 1 event baru."""
    event = {
        "topic": "test.topic",
        "event_id": "ev-001",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "pytest",
        "payload": {"data": 123}
    }

    response = await client.post("/publish", json=event)
    assert response.status_code == 202
    assert response.json()["queued_count"] == 1

    await asyncio.sleep(0.1)  # Beri waktu background task

    response_stats = await client.get("/stats")
    data = response_stats.json()
    assert data["received_events"] == 1
    assert data["unique_events"] == 1
    assert data["duplicates"] == 0

async def test_deduplication_logic(client):
    """
    Tes logika deduplikasi (1 unik, 2 duplikat).
    Ini adalah tes yang logikanya diperbaiki.
    """
    event_id = "ev-dedup-001"
    event_payload = {
        "topic": "dedup.test",
        "event_id": event_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "pytest",
        "payload": {}
    }

    await client.post("/publish", json=event_payload)  # 1 (Unik)
    await client.post("/publish", json=event_payload)  # 2 (Duplikat)
    await client.post("/publish", json=event_payload)  # 3 (Duplikat)
    await asyncio.sleep(0.2)  # Beri waktu untuk 3 background task

    response_stats = await client.get("/stats")
    data = response_stats.json()

    # --- ASSERTIONS YANG BENAR ---
    assert data["received_events"] == 3
    assert data["unique_events"] == 1  # <-- HARUS 1
    assert data["duplicates"] == 2     # <-- HARUS 2

async def test_publish_batch_events(client):
    """Tes 1 batch berisi 2 event unik."""
    events = {
        "events": [
            {
                "topic": "batch.test", "event_id": "ev-batch-001",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": "pytest-batch", "payload": {}
            },
            {
                "topic": "batch.test", "event_id": "ev-batch-002",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": "pytest-batch", "payload": {}
            }
        ]
    }

    response = await client.post("/publish", json=events)
    assert response.status_code == 202
    assert response.json()["queued_count"] == 2

    await asyncio.sleep(0.1)  # Beri waktu background task
    response_stats = await client.get("/stats")
    data = response_stats.json()
    assert data["received_events"] == 2  # <-- Tes ketat (==)
    assert data["unique_events"] == 2

async def test_get_events_with_topic_filter(client):
    """Tes GET /events dan filter by topic."""
    ev1 = {"topic": "topic.a", "event_id": "ev-a1", "timestamp": datetime.now(timezone.utc).isoformat(), "source": "p", "payload": {}}
    ev2 = {"topic": "topic.b", "event_id": "ev-b1", "timestamp": datetime.now(timezone.utc).isoformat(), "source": "p", "payload": {}}

    await client.post("/publish", json=ev1)
    await client.post("/publish", json=ev2)
    await asyncio.sleep(0.1)  # Beri waktu background task

    resp_all = await client.get("/events")
    assert resp_all.status_code == 200
    assert len(resp_all.json()) == 2  # <-- Tes ketat (==)

    resp_filter = await client.get("/events?topic=topic.a")
    assert resp_filter.status_code == 200
    assert len(resp_filter.json()) == 1
    assert resp_filter.json()[0]["event_id"] == "ev-a1"