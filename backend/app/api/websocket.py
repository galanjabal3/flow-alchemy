"""WebSocket endpoint for realtime execution updates."""

import json
import asyncio
import structlog
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user_from_token
from app.core.redis import get_redis
from app.core.events import EXECUTION_EVENTS_CHANNEL
from app.models.workflow import User, Execution

logger = structlog.get_logger()

router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections for execution updates."""

    def __init__(self):
        # execution_id -> set of websockets
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, execution_id: str):
        """Accept and register a WebSocket connection."""
        await websocket.accept()
        if execution_id not in self.active_connections:
            self.active_connections[execution_id] = set()
        self.active_connections[execution_id].add(websocket)

    def disconnect(self, websocket: WebSocket, execution_id: str):
        """Remove a WebSocket connection."""
        if execution_id in self.active_connections:
            self.active_connections[execution_id].discard(websocket)
            if not self.active_connections[execution_id]:
                del self.active_connections[execution_id]

    async def broadcast(self, execution_id: str, message: dict):
        """Send a message to all connections for an execution."""
        if execution_id in self.active_connections:
            dead_connections = []
            for connection in self.active_connections[execution_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    dead_connections.append(connection)

            # Clean up dead connections
            for conn in dead_connections:
                self.active_connections[execution_id].discard(conn)


# Global connection manager
manager = ConnectionManager()


async def redis_event_listener():
    """Listen to Redis Pub/Sub and broadcast to WebSocket clients."""
    pubsub = None
    try:
        client = await get_redis()
        pubsub = client.pubsub()
        await pubsub.subscribe(EXECUTION_EVENTS_CHANNEL)

        logger.info("redis_event_listener_started", channel=EXECUTION_EVENTS_CHANNEL)

        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    event_data = json.loads(message["data"])
                    execution_id = event_data.get("execution_id")

                    if execution_id and execution_id in manager.active_connections:
                        await manager.broadcast(execution_id, event_data)

                except json.JSONDecodeError as e:
                    logger.error("event_json_parse_failed", error=str(e))
                except Exception as e:
                    logger.error("event_broadcast_failed", error=str(e))

    except asyncio.CancelledError:
        logger.info("redis_event_listener_cancelled")
    except Exception as e:
        logger.error("redis_event_listener_failed", error=str(e))
    finally:
        if pubsub:
            try:
                await pubsub.unsubscribe(EXECUTION_EVENTS_CHANNEL)
            except Exception:
                pass

@router.websocket("/ws/executions/{execution_id}")
async def websocket_execution(
    websocket: WebSocket,
    execution_id: str,
    token: str = Query(None),
):
    """WebSocket endpoint for realtime execution updates.

    Connect with: ws://localhost:8000/api/workflows/ws/executions/{id}?token={jwt}

    Note: Token is passed as query param for simplicity. In production,
    consider using WebSocket subprotocol headers for better security.
    """
    # Validate execution_id is numeric
    if not execution_id or not execution_id.isdigit():
        await websocket.close(code=4000, reason="Invalid execution ID")
        return

    # Authenticate
    if not token:
        await websocket.close(code=4001, reason="Token required")
        return

    try:
        user = get_current_user_from_token(token)
    except Exception:
        await websocket.close(code=4001, reason="Invalid token")
        return

    # Check execution exists and user owns it (single DB call)
    db = next(get_db())
    try:
        execution = db.query(Execution).filter(
            Execution.id == int(execution_id),
            Execution.user_id == user.id,
        ).first()
        if not execution:
            await websocket.close(code=4004, reason="Execution not found or unauthorized")
            return

        # Send current status
        await websocket.send_json({
            "execution_id": execution_id,
            "event_type": "connected",
            "status": execution.status,
            "output_data": execution.output_data,
            "error_log": execution.error_log,
        })
    finally:
        db.close()

    # Connect
    await manager.connect(websocket, execution_id)

    try:
        # Keep connection alive and handle incoming messages
        while True:
            # Wait for any message (ping/pong or client messages)
            data = await websocket.receive_text()

            # Handle ping
            if data == "ping":
                await websocket.send_text("pong")

    except WebSocketDisconnect:
        manager.disconnect(websocket, execution_id)
    except Exception:
        manager.disconnect(websocket, execution_id)
