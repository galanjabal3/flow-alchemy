from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.core.redis import get_redis, close_redis, redis_ping
from app.api import auth, workflows, nodes, websocket, versions, replay, compiler, credentials, scheduler, webhooks, debug
import asyncio

setup_logging(log_level="INFO")
logger = get_logger(__name__)

# Background task for Redis event listener
_redis_listener_task = None


async def start_redis_listener():
    """Start the Redis event listener in background."""
    from app.api.websocket import redis_event_listener
    await redis_event_listener()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("FlowAlchemy API starting up", app_name=settings.APP_NAME)

    # Initialize Redis
    try:
        redis_client = await get_redis()
        if await redis_ping():
            logger.info("redis_connected", url=settings.REDIS_URL)
        else:
            logger.warning("redis_unavailable", url=settings.REDIS_URL)
    except Exception as e:
        logger.warning("redis_init_failed", error=str(e))

    # Start Redis event listener in background
    global _redis_listener_task
    _redis_listener_task = asyncio.create_task(start_redis_listener())
    logger.info("redis_listener_started")

    yield

    # Shutdown
    if _redis_listener_task:
        _redis_listener_task.cancel()
        try:
            await _redis_listener_task
        except asyncio.CancelledError:
            pass

    await close_redis()
    logger.info("FlowAlchemy API shutting down")


app = FastAPI(
    title=settings.APP_NAME,
    description="Visual workflow automation engine — drag-and-drop builder that compiles to executable Python",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(workflows.router, prefix="/api/workflows", tags=["Workflows"])
app.include_router(nodes.router, prefix="/api/nodes", tags=["Nodes"])
app.include_router(websocket.router, prefix="/api/workflows", tags=["WebSocket"])
app.include_router(versions.router, prefix="/api", tags=["Versions"])
app.include_router(replay.router, prefix="/api", tags=["Replay"])
app.include_router(compiler.router, prefix="/api", tags=["Compiler"])
app.include_router(credentials.router, prefix="/api", tags=["Credentials"])
app.include_router(scheduler.router, prefix="/api", tags=["Scheduler"])
app.include_router(webhooks.router, prefix="/api", tags=["Webhooks"])
app.include_router(debug.router, prefix="/api", tags=["Debug"])


@app.get("/health")
async def health_check():
    """Health check endpoint with Redis and DB connectivity."""
    from app.core.redis import redis_ping
    from app.core.database import SessionLocal

    health = {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": "0.1.0",
        "redis": "unknown",
        "database": "unknown",
    }

    # Check Redis
    try:
        redis_ok = await redis_ping()
        health["redis"] = "connected" if redis_ok else "disconnected"
    except Exception:
        health["redis"] = "error"

    # Check Database
    try:
        db = SessionLocal()
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        db.close()
        health["database"] = "connected"
    except Exception:
        health["database"] = "error"

    # Overall status
    if health["redis"] != "connected" or health["database"] != "connected":
        health["status"] = "degraded"

    return health
