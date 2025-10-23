# main.py



from fastapi import FastAPI, Request

from datetime import datetime, timezone

from src.aggregator import Aggregator

from contextlib import asynccontextmanager

import logging

import os

import asyncio # <-- Import asyncio



# Setup logging

logging.basicConfig(level=logging.INFO)

log = logging.getLogger("uvicorn")



os.makedirs("data", exist_ok=True)

aggregator = Aggregator()



@asynccontextmanager

async def lifespan(app: FastAPI):

    """

    Mengelola startup/shutdown.

    Sekarang juga mengelola siklus hidup worker.

    """

    log.info("Server starting up...")

    await aggregator.initialize() # <-- Ini memulai worker

    yield

    log.info("Server shutting down.")

    await aggregator.shutdown() # <-- Ini menghentikan worker



app = FastAPI(

    title="PubSub Aggregator Service (Queue Worker)",

    lifespan=lifespan

)



START_TIME = datetime.now(timezone.utc).isoformat()



@app.post("/publish", status_code=202)

async def publish_event(request: Request):

    """

    Endpoint ini sekarang sangat cepat.

    Hanya memasukkan event ke queue, tidak memblokir.

    """

    body = await request.json()



    if "events" in body:

        events = body["events"]

        # 'await' di sini hanya menunggu event dimasukkan ke queue (in-memory)

        await aggregator.queue_batch(events)

        return {"status": "accepted", "queued_count": len(events)}

    else:

        await aggregator.queue_event(body)

        return {"status": "accepted", "queued_count": 1}



@app.get("/events")

async def get_events(topic: str = None):

    return await aggregator.get_events(topic)



@app.get("/stats")

async def get_stats():

    stats = await aggregator.get_stats()

    stats["start_time"] = START_TIME

    return stats



# --- Main execution (untuk development) ---

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(

        "main:app",

        host="0.0.0.0",

        port=8080,

        reload=True,

        log_level="info"

    )