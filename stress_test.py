# stress_test.py



import asyncio

import httpx

import random

import string

from datetime import datetime, timezone



SERVER_URL = "http://localhost:8080"

TOTAL_EVENTS = 5000

DUPLICATE_RATIO = 0.25  # 25% duplikasi

BATCH_SIZE = 100

MAX_WAIT_SEC = 30





def random_id(length=8):

    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))





def generate_events():

    """Generate 5000 event dengan sebagian duplikat."""

    unique_count = int(TOTAL_EVENTS * (1 - DUPLICATE_RATIO))

    duplicate_count = TOTAL_EVENTS - unique_count



    # Buat event unik dulu

    base_events = []

    for _ in range(unique_count):

        event_id = f"evt-{random_id()}"

        event = {

            "topic": "stress.test",

            "event_id": event_id,

            "timestamp": datetime.now(timezone.utc).isoformat(),

            "source": "stress_tester",

            "payload": {"random": random.randint(0, 1000)},

        }

        base_events.append(event)



    # Gandakan beberapa sebagai duplikat

    duplicates = random.choices(base_events, k=duplicate_count)

    all_events = base_events + duplicates

    random.shuffle(all_events)

    return all_events





async def send_batch(client, batch, idx):

    try:

        response = await client.post(f"{SERVER_URL}/publish", json={"events": batch})

        if response.status_code != 202:

            print(f"❌ Gagal batch {idx}: {response.status_code}")

    except Exception as e:

        print(f"❌ Error batch {idx}: {e}")





async def run_test():

    print(f"Memulai stress test: {TOTAL_EVENTS} event ({DUPLICATE_RATIO*100:.1f}% duplikasi)...")



    all_events = generate_events()



    async with httpx.AsyncClient(timeout=10) as client:

        # Kirim batch secara paralel

        tasks = []

        for i in range(0, len(all_events), BATCH_SIZE):

            batch = all_events[i:i + BATCH_SIZE]

            task = asyncio.create_task(send_batch(client, batch, i // BATCH_SIZE))

            tasks.append(task)

            if len(tasks) >= 10:  # batasi concurrency agar stabil

                await asyncio.gather(*tasks)

                tasks.clear()



        # Tunggu batch terakhir

        if tasks:

            await asyncio.gather(*tasks)



    print(f"\nSelesai mengirim {TOTAL_EVENTS} event.")

    print("Menunggu server memproses semua event (max 30 detik)...")



    # Polling ke endpoint /stats

    async with httpx.AsyncClient(timeout=10) as client:

        for _ in range(MAX_WAIT_SEC):

            try:

                r = await client.get(f"{SERVER_URL}/stats")

                stats = r.json()

                recv = stats.get("received_events", 0)

                print(f"  ... Status proses: {recv} / {TOTAL_EVENTS}")

                if recv >= TOTAL_EVENTS:

                    break

            except Exception:

                pass

            await asyncio.sleep(1)



        print("\n--- HASIL STATISTIK FINAL ---")

        print(f"  Received Events:     {stats.get('received_events')}")

        print(f"  Unique Events:       {stats.get('unique_events')}")

        print(f"  Duplicates Dropped:  {stats.get('duplicates')}")

        print("-------------------------------")



        # Pastikan hasil akhir masuk akal

        assert stats.get("received_events", 0) >= TOTAL_EVENTS * 0.9, "Terlalu sedikit event diterima!"

        assert stats.get("duplicates", 0) > 0, "Tidak ada duplikasi yang terdeteksi!"





if __name__ == "__main__":

    asyncio.run(run_test())