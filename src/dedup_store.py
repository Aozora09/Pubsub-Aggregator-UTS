# src/dedup_store.py

import aiosqlite
import logging
import os  # <-- Pastikan 'os' di-import
from datetime import datetime, timezone

log = logging.getLogger("uvicorn")

# --- PERUBAHAN KRUSIAL DIMULAI DI SINI ---

# 1. Tentukan path absolut yang SAMA PERSIS dengan di docker-compose.yml
DB_DIR = "/app/data" 

# 2. Buat path lengkap ke file database
DB_PATH = os.path.join(DB_DIR, "dedup_store.db")

# --- PERUBAHAN KRUSIAL SELESAI ---


class DedupStore:
    def __init__(self, path: str = DB_PATH):
        """Konstruktor, sekarang menggunakan path absolut."""
        self.path = path
        
        # --- PERUBAHAN PENTING ---
        # 3. Pastikan direktori /app/data ADA sebelum mencoba menulis
        #    Ini penting agar aiosqlite tidak gagal.
        try:
            os.makedirs(DB_DIR, exist_ok=True)
            log.info(f"Folder persistensi {DB_DIR} dipastikan ada.")
        except OSError as e:
            log.error(f"GAGAL membuat direktori {DB_DIR}: {e}", exc_info=True)
        # -------------------------
            
        log.info(f"DedupStore akan menggunakan DB di: {self.path}")


    async def init_db(self):
        """Memastikan database dan tabel sudah ada."""
        try:
            async with aiosqlite.connect(self.path) as db:
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS processed_events (
                        topic TEXT,
                        event_id TEXT,
                        processed_at TEXT,
                        PRIMARY KEY (topic, event_id)
                    )
                """)
                await db.commit()
            log.info(f"Database berhasil diinisialisasi di {self.path}")
        except Exception as e:
            log.error(f"GAGAL TOTAL inisialisasi database di {self.path}: {e}", exc_info=True)
            # Ini adalah error fatal, kita harus melemparnya lagi
            raise e


    async def check_and_add_batch(self, events: list) -> list:
        """
        Memeriksa dan menyisipkan seluruh BATCH event dalam SATU TRANSAKSI.
        Aman dan cepat untuk aiosqlite.
        (Fungsi ini sudah benar, tidak perlu diubah)
        """
        new_events = []
        timestamp = datetime.now(timezone.utc).isoformat()
        
        async with aiosqlite.connect(self.path) as db:
            try:
                # Mulai transaksi manual
                await db.execute("BEGIN")
                
                for event in events:
                    topic = event.get("topic", "unknown")
                    event_id = event.get("event_id")
                    if not topic or not event_id:
                        continue  # Lewati event yang tidak valid

                    try:
                        # Coba masukkan. Ini akan gagal jika PRIMARY KEY (topic, event_id) sudah ada.
                        await db.execute(
                            "INSERT INTO processed_events (topic, event_id, processed_at) VALUES (?, ?, ?)",
                            (topic, event_id, timestamp)
                        )
                        # Jika berhasil, ini adalah event baru
                        new_events.append(event)
                    except aiosqlite.IntegrityError:
                        # Event duplikat (PRIMARY KEY conflict), abaikan
                        pass

                # Commit transaksi
                await db.commit()

            except Exception as e:
                await db.rollback()
                log.error(f"❌ Error saat memproses batch: {e}", exc_info=True)

        return new_events
    
    
    async def get_initial_unique_count(self) -> int:
        """
        Menghitung event unik yang sudah ada di DB saat startup.
        Ini untuk memuat ulang state 'unique_events' yang persistent.
        """
        count = 0
        try:
            # Kita tidak perlu init_db() di sini, karena kita asumsikan 
            # itu sudah dipanggil oleh aggregator.
            async with aiosqlite.connect(self.path) as db:
                async with db.execute("SELECT COUNT(event_id) FROM processed_events") as cursor:
                    row = await cursor.fetchone()
                    if row:
                        count = row[0]
            log.info(f"LOAD STATE: Berhasil memuat state. Ditemukan {count} event unik yang sudah ada.")
            return count
        except Exception as e:
            # Ini akan gagal jika file DB belum ada atau tabelnya belum dibuat
            # Ini NORMAL pada run pertama.
            log.warning(f"LOAD STATE: Tidak dapat memuat initial count (DB baru?): {e}")
            return 0