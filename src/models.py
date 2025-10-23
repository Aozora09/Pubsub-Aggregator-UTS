from pydantic import BaseModel
from typing import Dict, Any, List, Optional


class Event(BaseModel):
    topic: str
    event_id: str
    timestamp: str
    source: str
    payload: Dict[str, Any]


class EventBatch(BaseModel):
    events: List[Event]


class Stats(BaseModel):
    received_events: int
    unique_events: int
    duplicates: int
    last_updated: Optional[str]
