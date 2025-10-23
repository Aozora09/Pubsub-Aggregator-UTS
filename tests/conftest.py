# tests/conftest.py

import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# Import 'app' DAN 'aggregator' global dari main.py
from main import app, aggregator

@pytest_asyncio.fixture(scope="function")
async def client():
    """
    Fixture ini membuat test client DAN mereset state aplikasi
    SEBELUM setiap fungsi tes dijalankan.
    """
    
    # --- SETUP (Sebelum setiap tes) ---
    # Panggil metode helper reset kita di aggregator
    # Ini akan membersihkan stats, cache, DAN file database
    await aggregator.reset_for_testing()
    
    # --- Yield Client ---
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    
    # --- TEARDOWN (Setelah setiap tes) ---
    # (Opsional) Reset lagi setelah selesai
    await aggregator.reset_for_testing()