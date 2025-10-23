# src/database.py

import aiosqlite
import logging
from datetime import datetime, timezone

# Path ke database, akan dibuat di dalam folder /data
DB_PATH = "data/dedup_store.db"

# Siapkan logging
log = logging.getLogger("uvicorn")

async def init_db():
    """
    Membuat tabel 'processed_events' jika belum ada.
    Ini harus dipanggil saat aplikasi (FastAPI) startup.
    """
    log.info(f"Menginisialisasi database di {DB_PATH}...")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS processed_events (
                topic TEXT,
                event_id TEXT,
                processed_at TEXT,
                PRIMARY KEY (topic, event_id)
            )
        """)
        await db.commit()
    log.info("Database berhasil diinisialisasi.")

async def check_and_add_event(topic: str, event_id: str) -> bool:
    """
    Mencoba menambahkan event ke database.
    Ini adalah operasi atomik berkat PRIMARY KEY.

    Mengembalikan:
        True: Jika event BARU dan berhasil ditambahkan.
        False: Jika event DUPLIKAT (gagal ditambahkan karena constraint).
    """
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                "INSERT INTO processed_events (topic, event_id, processed_at) VALUES (?, ?, ?)",
                (topic, event_id, datetime.now(timezone.utc).isoformat())
            )
            await db.commit()
            return True  # Berhasil INSERT, ini event baru
        
        except aiosqlite.IntegrityError:
            # Gagal INSERT karena PRIMARY KEY (topic, event_id) sudah ada.
            # Ini adalah DUPLIKAT.
            return False
        
        except Exception as e:
            log.error(f"Error database saat memeriksa event {event_id}: {e}")
            return False # Anggap duplikat (atau gagal) jika ada error lain