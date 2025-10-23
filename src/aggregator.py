# src/aggregator.py

import asyncio
from datetime import datetime, timezone
from .dedup_store import DedupStore
import logging
import os

log = logging.getLogger("uvicorn")

class Aggregator:
    def __init__(self):
        self.store = DedupStore()
        # Queue ini adalah inti dari arsitektur performa tinggi
        self.queue = asyncio.Queue(maxsize=10000)
        self.worker_task = None
        
        self.topics_cache = {} 
        self.stats = {
            "received_events": 0,
            "unique_events": 0,
            "duplicates": 0,
            "last_updated": None,
        }
        # Lock ini HANYA melindungi stats & cache (bukan database)
        self.lock = asyncio.Lock() 

    async def initialize(self):
        """Dipanggil oleh 'lifespan' untuk inisialisasi DB DAN memulai worker."""
        await self.store.init_db()
        # Memulai satu worker tunggal yang akan memproses queue
        self.worker_task = asyncio.create_task(self._consumer_worker())
        log.info("Consumer worker started.")

    async def shutdown(self):
        """Dipanggil oleh 'lifespan' untuk menghentikan worker."""
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                log.info("Consumer worker stopped.")

    async def _consumer_worker(self):
        """
        Worker TUNGGAL yang berjalan di background.
        Ini adalah *satu-satunya* proses yang menyentuh database.
        """
        while True:
            try:
                # 1. Menunggu event pertama (jika queue kosong)
                first_event = await self.queue.get()
                
                # 2. Mengambil sisa batch (jika ada)
                batch = [first_event]
                batch_limit = 100 # Proses maks 100 event per transaksi
                
                # Ambil event dari queue sampai batch penuh atau queue kosong
                while len(batch) < batch_limit and not self.queue.empty():
                    batch.append(self.queue.get_nowait())
                    
                # 3. Proses batch ini secara internal (menyentuh DB)
                await self._process_batch_internal(batch)
                
                # 4. Tandai semua event di queue sebagai selesai
                for _ in batch:
                    self.queue.task_done()
                    
            except asyncio.CancelledError:
                log.info("Consumer worker stopping...")
                return
            except Exception as e:
                log.error(f"Error di consumer worker: {e}", exc_info=True)
                await asyncio.sleep(1)

    # --- API-facing methods (Sangat Cepat) ---
    async def queue_event(self, event: dict):
        """Dipanggil oleh /publish (single event)"""
        await self.queue.put(event)

    async def queue_batch(self, events: list):
        """Dipanggil oleh /publish (batch event)"""
        for event in events:
            await self.queue.put(event)

    # --- Internal worker method (Lambat, DB-heavy) ---
    async def _process_batch_internal(self, events: list):
        """HANYA dipanggil oleh _consumer_worker."""
        if not events:
            return

        try:
            # 1. Panggil DB (efisien)
            new_events = await self.store.check_and_add_batch(events)
        except Exception as e:
            log.error(f"Gagal memproses batch di DB: {e}", exc_info=True)
            return

        # 2. Hitung statistik
        num_received = len(events)
        num_new = len(new_events)
        num_dups = num_received - num_new
        
        # 3. Update statistik (in-memory)
        async with self.lock:
            self.stats["received_events"] += num_received
            self.stats["unique_events"] += num_new
            self.stats["duplicates"] += num_dups
            
            if num_new > 0:
                self.stats["last_updated"] = datetime.now(timezone.utc).isoformat()
                for event in new_events:
                    topic = event.get("topic", "unknown")
                    if topic not in self.topics_cache:
                        self.topics_cache[topic] = []
                    self.topics_cache[topic].append(event)
    
    # --- Metode helper ---
    async def get_stats(self):
        async with self.lock:
            stats_copy = dict(self.stats)
            stats_copy["unique_topics"] = len(self.topics_cache)
            return stats_copy

    async def get_events(self, topic: str = None):
        async with self.lock:
            if topic:
                return self.topics_cache.get(topic, [])
            all_events = []
            for ev_list in self.topics_cache.values():
                all_events.extend(ev_list)
            return all_events
            
    async def reset_for_testing(self):
        """Membersihkan state untuk pytest."""
        if self.worker_task:
            self.worker_task.cancel()
            try: await self.worker_task
            except asyncio.CancelledError: pass
        
        while not self.queue.empty():
            self.queue.get_nowait()
            
        async with self.lock:
            self.stats = {
                "received_events": 0, "unique_events": 0,
                "duplicates": 0, "last_updated": None,
            }
            self.topics_cache.clear()
        
        db_path = "data/dedup_store.db"
        if os.path.exists(db_path):
            os.remove(db_path)
        
        await self.initialize()
        
    # ... (di dalam class Aggregator) ...

    async def initialize(self):
        """Dipanggil oleh 'lifespan' untuk inisialisasi DB DAN memulai worker."""
        
        # 1. Pastikan tabel ada (penting untuk langkah 2)
        await self.store.init_db()
        
        # --- PERBAIKAN DI SINI ---
        # 2. Hitung state dari DB yang persistent
        initial_unique_count = await self.store.get_initial_unique_count()
        
        # 3. Set stats in-memory ke state yang ada di DB
        async with self.lock:
            # Set 'unique_events' ke hitungan yang ada di DB
            self.stats["unique_events"] = initial_unique_count
            
            # Stats lain (received, duplicates) dimulai dari 0 untuk SESI INI.
            # Ini adalah keputusan desain, tapi ini yang paling logis.
            self.stats["received_events"] = 0
            self.stats["duplicates"] = 0
            
        # 4. Memulai satu worker tunggal yang akan memproses queue
        self.worker_task = asyncio.create_task(self._consumer_worker())
        log.info("Consumer worker started.")