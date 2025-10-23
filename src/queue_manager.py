import asyncio
from .models import EventModel

# Queue global untuk pipeline publisher → consumer
EVENT_QUEUE: asyncio.Queue[EventModel] = asyncio.Queue(maxsize=10000)
