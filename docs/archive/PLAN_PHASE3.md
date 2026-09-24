# Phase 3: Async Runtime — Detailed Implementation Plan

## Overview

Phase 3 transforms FlowAlchemy from synchronous execution to a production-grade async runtime with Redis Queue, background workers, and realtime updates.

## Current State (What We Have)

```
POST /workflows/{id}/run
  → Creates Execution record (status="running")
  → Runs WorkflowEngine.execute() SYNCHRONOUSLY
  → Waits for completion
  → Returns result

Problem:
- API blocks until workflow finishes
- No retry on failure
- No timeout enforcement
- No realtime updates
- No concurrency control
```

## Target State (What We'll Build)

```
POST /workflows/{id}/run
  → Creates Execution record (status="queued")
  → Enqueues job to Redis
  → Returns execution_id immediately

Worker (separate process):
  → Picks up job from Redis
  → Updates status to "running"
  → Executes workflow
  → Handles retry/timeout
  → Updates status to "completed"/"failed"
  → Publishes events to Redis Pub/Sub

WebSocket (optional):
  → Client subscribes to execution events
  → Realtime status updates in UI
```

---

## Architecture

### Component Diagram

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│   FastAPI   │────▶│   Redis     │
│   (React)   │     │   (API)     │     │   (Queue)   │
└─────────────┘     └─────────────┘     └─────────────┘
       │                                        │
       │ WebSocket                              │
       │                                        ▼
       │                                   ┌─────────────┐
       └───────────────────────────────────│   Worker    │
                                           │   (Async)   │
                                           └─────────────┘
```

### Data Flow

1. **API Layer**: Validates request, creates Execution record, enqueues job
2. **Redis Queue**: Stores pending jobs (FIFO)
3. **Worker**: Processes jobs, executes workflow, updates DB
4. **Redis Pub/Sub**: Publishes execution events
5. **WebSocket**: Streams events to frontend

---

## Implementation Plan

### Step 1: Redis Infrastructure

**Files to create:**
- `backend/app/core/redis.py` — Redis connection pool + client
- `backend/app/core/queue.py` — Job queue abstraction
- `backend/app/core/events.py` — Redis Pub/Sub for execution events

**Files to modify:**
- `backend/app/core/config.py` — Add Redis URL setting
- `backend/requirements.txt` — Add redis, websockets

**Acceptance Criteria:**
- [ ] Redis connection pool initialized on startup
- [ ] Jobs can be enqueued and dequeued
- [ ] Events can be published and subscribed
- [ ] Connection errors handled gracefully

---

### Step 2: Job Queue

**Files to create:**
- `backend/app/core/job.py` — Job dataclass (execution_id, workflow_id, etc.)

**Files to modify:**
- `backend/app/core/queue.py` — Implement job serialization

**Acceptance Criteria:**
- [ ] Jobs serialized as JSON
- [ ] Jobs deserialized correctly
- [ ] Job priority supported (optional)
- [ ] Job TTL supported (optional)

---

### Step 3: Worker

**Files to create:**
- `backend/app/worker.py` — Worker entry point
- `backend/app/core/worker.py` — Worker logic (poll, execute, update)

**Files to modify:**
- None (worker is separate process)

**Acceptance Criteria:**
- [ ] Worker polls Redis for jobs
- [ ] Worker executes workflow
- [ ] Worker updates Execution status in DB
- [ ] Worker handles errors gracefully
- [ ] Worker can be stopped gracefully (SIGTERM)

---

### Step 4: Execution State Machine

**Files to create:**
- `backend/app/core/state_machine.py` — Execution state transitions

**Files to modify:**
- `backend/app/core/workflow_engine.py` — Use state machine

**Acceptance Criteria:**
- [ ] States: queued → running → completed/failed/cancelled
- [ ] Invalid transitions rejected
- [ ] State transitions logged
- [ ] State persisted to DB

---

### Step 5: Retry Mechanism

**Files to modify:**
- `backend/app/core/worker.py` — Add retry logic
- `backend/app/core/config.py` — Add retry settings

**Acceptance Criteria:**
- [ ] Configurable max retries (default: 3)
- [ ] Exponential backoff (1s, 2s, 4s)
- [ ] Retry on specific errors (network, timeout)
- [ ] No retry on validation errors
- [ ] Retry count persisted to DB

---

### Step 6: Timeout Enforcement

**Files to modify:**
- `backend/app/core/worker.py` — Add timeout logic
- `backend/app/core/config.py` — Add timeout settings

**Acceptance Criteria:**
- [ ] Configurable timeout per workflow (default: 300s)
- [ ] Configurable timeout per node (default: 30s)
- [ ] Timeout triggers failure + retry
- [ ] Timeout logged

---

### Step 7: Resource Limits

**Files to modify:**
- `backend/app/core/worker.py` — Add resource checks
- `backend/app/core/config.py` — Add resource settings

**Acceptance Criteria:**
- [ ] Max concurrent workflows per user (default: 5)
- [ ] Max concurrent workflows total (default: 10)
- [ ] Limit exceeded → queued with priority
- [ ] Limit logged

---

### Step 8: Idempotency

**Files to modify:**
- `backend/app/core/worker.py` — Add idempotency check
- `backend/app/models/workflow.py` — Add idempotency key field

**Acceptance Criteria:**
- [ ] Execution ID used as idempotency key
- [ ] Duplicate jobs rejected
- [ ] Partial failures handled correctly

---

### Step 9: API Changes

**Files to modify:**
- `backend/app/api/workflows.py` — Async run endpoint
- `backend/app/schemas/workflow.py` — Add queue status to response

**Acceptance Criteria:**
- [ ] POST /workflows/{id}/run returns immediately
- [ ] Response includes execution_id + status="queued"
- [ ] GET /executions/{id} returns current status
- [ ] Rate limiting still works

---

### Step 10: Execution Events

**Files to modify:**
- `backend/app/core/worker.py` — Publish events on state change
- `backend/app/core/events.py` — Event types defined

**Acceptance Criteria:**
- [ ] Events: started, node_started, node_completed, node_failed, completed, failed
- [ ] Events published to Redis Pub/Sub
- [ ] Events include execution_id, node_id, status, data

---

### Step 11: WebSocket (Optional)

**Files to create:**
- `backend/app/api/websocket.py` — WebSocket endpoint

**Files to modify:**
- `backend/app/main.py` — Register WebSocket route

**Acceptance Criteria:**
- [ ] Client can connect to /ws/executions/{id}
- [ ] Client receives realtime events
- [ ] Connection closed gracefully
- [ ] Auth required (token in query param)

---

### Step 12: Service Layer Cleanup

**Files to create:**
- `backend/app/services/workflow_service.py` — Business logic
- `backend/app/services/execution_service.py` — Execution logic

**Files to modify:**
- `backend/app/api/workflows.py` — Use services

**Acceptance Criteria:**
- [ ] API layer is thin (validation + response)
- [ ] Business logic in services
- [ ] Services are testable
- [ ] No duplicate code

---

## Database Migration

**New fields in `executions` table:**
- `idempotency_key` (String, unique, nullable)
- `retry_count` (Integer, default=0)
- `max_retries` (Integer, default=3)
- `worker_id` (String, nullable)
- `queued_at` (DateTime, nullable)

**Migration file:** `backend/alembic/versions/004_add_async_runtime_fields.py`

---

## Configuration

**New environment variables:**
```bash
# Redis
REDIS_URL=redis://localhost:6379/0

# Worker
WORKER_CONCURRENCY=10
WORKER_POLL_INTERVAL=1.0

# Retry
MAX_RETRIES=3
RETRY_BACKOFF_BASE=2

# Timeout
WORKFLOW_TIMEOUT=300
NODE_TIMEOUT=30

# Resource Limits
MAX_CONCURRENT_PER_USER=5
MAX_CONCURRENT_TOTAL=10
```

---

## Testing Strategy

**Unit Tests:**
- State machine transitions
- Job serialization/deserialization
- Retry logic
- Timeout logic

**Integration Tests:**
- API → Redis → Worker → DB
- Worker → Redis Pub/Sub → WebSocket
- Rate limiting + queue

**E2E Tests:**
- Run workflow → see realtime updates
- Fail workflow → see retry
- Timeout workflow → see failure

---

## Rollout Plan

1. **Step 1-3**: Redis + Queue + Worker (core async)
2. **Step 4-8**: State machine + Retry + Timeout + Limits + Idempotency (reliability)
3. **Step 9-10**: API changes + Events (integration)
4. **Step 11-12**: WebSocket + Service layer (polish)

---

## Dependencies

**New packages:**
- `redis` (async Redis client)
- `websockets` (WebSocket support)

**Infrastructure:**
- Redis server (local or Docker)

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Redis down | High | Fallback to sync execution |
| Worker crash | High | Auto-restart + retry |
| Memory leak | Medium | Resource limits + monitoring |
| Race conditions | Medium | Idempotency + locks |

---

## Success Criteria

- [ ] Workflows execute asynchronously
- [ ] API responds in <100ms
- [ ] Worker processes jobs reliably
- [ ] Retry works correctly
- [ ] Timeout enforced
- [ ] Realtime updates work (WebSocket)
- [ ] All existing tests still pass
- [ ] New tests added (target: 15+)
