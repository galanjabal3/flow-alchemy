"""Job data model for async execution."""

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional
import json
import uuid
from datetime import datetime, timezone


@dataclass
class Job:
    """Represents a workflow execution job in the queue."""

    execution_id: str
    workflow_id: int
    user_id: int
    trigger_data: Dict[str, Any] = field(default_factory=dict)
    idempotency_key: Optional[str] = None
    priority: int = 0  # Higher = more priority
    max_retries: int = 3
    retry_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self):
        """Validate job fields."""
        if not self.execution_id or not str(self.execution_id).isdigit():
            raise ValueError(f"execution_id must be numeric, got: {self.execution_id}")
        if self.workflow_id <= 0:
            raise ValueError(f"workflow_id must be positive, got: {self.workflow_id}")
        if self.user_id <= 0:
            raise ValueError(f"user_id must be positive, got: {self.user_id}")
        if self.max_retries < 0:
            raise ValueError(f"max_retries must be non-negative, got: {self.max_retries}")
        if self.retry_count < 0:
            raise ValueError(f"retry_count must be non-negative, got: {self.retry_count}")

    def to_json(self) -> str:
        """Serialize job to JSON."""
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, data: str) -> "Job":
        """Deserialize job from JSON with validation."""
        try:
            parsed = json.loads(data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")

        # Only accept known fields
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in parsed.items() if k in known_fields}

        return cls(**filtered)

    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary."""
        return asdict(self)
