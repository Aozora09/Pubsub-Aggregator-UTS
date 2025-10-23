import logging
from typing import Dict, List
from collections import defaultdict

from .queue_manager import EVENT_QUEUE
from .database import check_and_add_event
from .models import EventModel

log = logging.getLogger("uvicorn")

async def consumer_worker(stats: Dict[str, int], processed_events: Dict[str, List[EventModel]]):
    """
    Worker asinkron untuk memproses event dari queue.
    """
    log.info("Consumer worker started...")
    while True:
        try:
            event = await EVENT_QUEUE.get()
            is_new = await check_and_add_event(event.topic, event.event_id)

            if is_new:
                processed_events[event.topic].append(event)
                stats["unique_processed"] += 1
                log.info(f"Processed NEW event {event.event_id} ({event.topic})")
            else:
                stats["duplicate_dropped"] += 1
                log.warning(f"Duplicate event {event.event_id} detected")

            EVENT_QUEUE.task_done()
        except Exception as e:
            log.error(f"Consumer error: {e}", exc_info=True)
