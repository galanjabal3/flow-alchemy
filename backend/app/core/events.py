"""Redis Pub/Sub for execution events."""

import json
import structlog
from typing import Any, Dict, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from app.core.redis import get_redis

logger = structlog.get_logger()

# Event channels
EXECUTION_EVENTS_CHANNEL = "flowalchemy:executions:events"


@dataclass
class ExecutionEvent:
    """Represents an execution event."""

    execution_id: str
    event_type: str  # started, node_started, node_completed, node_failed, completed, failed
    node_id: Optional[str] = None
    status: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_json(self) -> str:
        """Serialize event to JSON."""
        return json.dumps(asdict(self))


async def publish_event(event: ExecutionEvent) -> bool:
    """Publish an execution event to Redis Pub/Sub."""
    try:
        client = await get_redis()
        event_json = event.to_json()
        await client.publish(EXECUTION_EVENTS_CHANNEL, event_json)

        logger.info(
            "event_published",
            execution_id=event.execution_id,
            event_type=event.event_type,
            node_id=event.node_id,
        )
        return True

    except Exception as e:
        logger.error("publish_event_failed", error=str(e), execution_id=event.execution_id)
        return False
