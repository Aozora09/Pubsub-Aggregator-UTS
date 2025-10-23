# publisher.py

# Versi sederhana dari stress_test untuk Docker Compose



import httpx

import asyncio

import uuid

import random

import time

from datetime import datetime, timezone



# Nama 'aggregator' akan di-resolve oleh jaringan internal Docker Compose

AGGREGATOR_URL = "http://aggregator:8080"



async def wait_for_aggregator():

    print("Publisher: Menunggu aggregator siap...")

    while True:

        try:

            async with httpx.AsyncClient(base_url=AGGREGATOR_URL) as client:

                resp = await client.get("/stats")

                if resp.status_code == 200:

                    print("Publisher: Aggregator siap.")

                    return

        except httpx.ConnectError:

            pass

        await asyncio.sleep(1)



async def main():

    await wait_for_aggregator()

   

    unique_ids = [str(uuid.uuid4()) for _ in range(100)]

    events = []

    for i in range(150): # Kirim 150 event (50 duplikat)

        ev_id = random.choice(unique_ids)

        events.append({

            "topic": "compose.test", "event_id": ev_id,

            "timestamp": datetime.now(timezone.utc).isoformat(),

            "source": "compose-publisher", "payload": {}

        })

       

    async with httpx.AsyncClient(base_url=AGGREGATOR_URL) as client:

        try:

            resp = await client.post("/publish", json={"events": events})

            print(f"Publisher: Mengirim 150 event. Status: {resp.status_code}")

        except Exception as e:

            print(f"Publisher: Gagal mengirim event: {e}")



if __name__ == "__main__":

    print("Publisher: Mulai...")

    asyncio.run(main())