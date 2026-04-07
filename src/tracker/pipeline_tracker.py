# backend/tracker/pipeline_tracker.py
"""
Real-time pipeline event tracker.
Designed to be Kafka-ready: swap _emit() to produce to a Kafka topic later.
For now: in-memory asyncio.Queue per session.
"""

import asyncio
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum


class StepStatus(str, Enum):
    PENDING  = "pending"
    RUNNING  = "running"
    DONE     = "done"
    SKIPPED  = "skipped"
    ERROR    = "error"


@dataclass
class PipelineEvent:
    session_id: str
    step:       str           # e.g. "greeter", "discovery", "builder"
    status:     StepStatus
    message:    str           # human-readable detail
    ts:         float = field(default_factory=time.time)
    meta:       Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d


# ── Global registry: session_id → asyncio.Queue ──────────────────
_SESSION_QUEUES: Dict[str, asyncio.Queue] = {}


def get_or_create_queue(session_id: str) -> asyncio.Queue:
    if session_id not in _SESSION_QUEUES:
        _SESSION_QUEUES[session_id] = asyncio.Queue()
    return _SESSION_QUEUES[session_id]


def drop_queue(session_id: str) -> None:
    _SESSION_QUEUES.pop(session_id, None)


async def emit(session_id: str, step: str, status: StepStatus,
               message: str, meta: Optional[Dict] = None) -> None:
    """
    Emit a pipeline event.
    LOCAL DEV  → puts into asyncio.Queue (SSE picks it up)
    KAFKA FUTURE → replace with: await kafka_producer.send(topic, event.to_dict())
    """
    event = PipelineEvent(
        session_id=session_id,
        step=step,
        status=status,
        message=message,
        meta=meta or {},
    )
    q = get_or_create_queue(session_id)
    await q.put(event)
    # ── KAFKA HOOK (future) ──────────────────────────────────────
    # await kafka_producer.send("pipeline-events", value=event.to_dict())
    # ────────────────────────────────────────────────────────────


async def emit_done(session_id: str) -> None:
    """Signal end of stream."""
    await emit(session_id, step="__done__", status=StepStatus.DONE, message="Pipeline complete")