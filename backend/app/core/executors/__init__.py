"""Node Executor Registry — maps node types to their executors."""

from typing import Dict, Type
from app.core.executors.base import BaseNodeExecutor
from app.core.executors.trigger import TriggerExecutor
from app.core.executors.http_request import HttpRequestExecutor
from app.core.executors.transform import TransformExecutor
from app.core.executors.condition import ConditionExecutor
from app.core.executors.delay import DelayExecutor
from app.core.executors.output import OutputExecutor


EXECUTOR_REGISTRY: Dict[str, BaseNodeExecutor] = {
    "trigger": TriggerExecutor(),
    "http_request": HttpRequestExecutor(),
    "transform": TransformExecutor(),
    "condition": ConditionExecutor(),
    "delay": DelayExecutor(),
    "output": OutputExecutor(),
}


def get_executor(node_type: str) -> BaseNodeExecutor:
    executor = EXECUTOR_REGISTRY.get(node_type)
    if executor is None:
        raise ValueError(f"No executor registered for node type: {node_type}")
    return executor
