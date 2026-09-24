# FlowAlchemy — Backend

FastAPI + SQLAlchemy 2 + Redis service powering the FlowAlchemy workflow automation engine: stores workflows/executions/credentials, runs the execution engine in a separate worker process, and exposes a REST + WebSocket API.

## Architecture

```
FastAPI (REST /api + WebSocket)      Worker (python -m app.worker)
        │                                    │
        └────────────┬───────────────────────┘
                     ▼
        Redis (queue + pub/sub events)
                     ▼
        PostgreSQL (workflows, executions, versions, credentials, webhooks)
```

- **API layer** (`app/api/`) — FastAPI routers: auth, workflows, nodes, versions, replay, compiler, scheduler, webhooks, debug, credentials, websocket.
- **Core engine** (`app/core/`) — graph validation, execution planner, workflow engine, per-node type executors (`http_request`, `transform`, `condition`, `delay`, `output`, `trigger`), state machine, encryption, SSRF protection, rate limiting, secure logging.
- **Worker** (`app/worker.py`) — consumes the Redis queue, is idempotent (idempotency keys + state-machine transitions), applies retries with exponential backoff + jitter, and streams progress events via pub/sub.
- **Migrations** — Alembic (`alembic/versions/`), applied automatically on container start via `entrypoint.sh`.

## Setup (local development)

Requires PostgreSQL and Redis (e.g. `docker compose up postgres redis` from the repo root).

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env     # set SECRET_KEY, DATABASE_URL, REDIS_URL
alembic upgrade head     # apply DB migrations
python run.py            # uvicorn API on :8000 (dev reload)
python -m app.worker     # separate terminal: job worker
```

## Environment variables

See `.env.example`. Validated at startup by `app/core/config.py` (`SECRET_KEY` ≥ 16 chars, `DATABASE_URL` required; timeouts, retries, and concurrency limits configurable).

| Variable | Default | Purpose |
|----------|---------|---------|
| `SECRET_KEY` | — (required) | JWT signing + credential-key derivation |
| `DATABASE_URL` | — (required) | PostgreSQL DSN |
| `REDIS_URL` | `redis://localhost:6379/0` | Queue + pub/sub |
| `ALLOWED_ORIGINS` | localhost list | CORS allow-list (no wildcard) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | JWT lifetime |
| `MAX_CONCURRENT_PER_USER` / `MAX_CONCURRENT_TOTAL` | `5` / `10` | Execution slots |
| `NODE_TIMEOUT` / `WORKFLOW_TIMEOUT` | `30s` / `300s` | Timeouts |
| `NODE_MAX_RETRIES` / `MAX_RETRIES` | `2` / `3` | Retry budgets |

## API

Swagger UI: http://localhost:8000/docs · ReDoc: http://localhost:8000/redoc · Health: http://localhost:8000/health

### Auth — prefix `/api/auth`
| Method | Path | Description |
|--------|------|-------------|
| POST | `/register` | Create account, returns API key |
| POST | `/login` | Login, returns JWT |
| GET | `/me` | Current profile |
| PUT | `/me` | Update profile |
| POST | `/change-password` | Change password |
| POST | `/regenerate-api-key` | Rotate hashed API key |

### Workflows — prefix `/api/workflows`
| Method | Path | Description |
|--------|------|-------------|
| GET / POST | `/` | List / create workflows |
| GET / PUT / DELETE | `/{workflow_id}` | Read / update / delete |
| POST | `/{workflow_id}/run` | Execute a workflow |
| POST | `/{workflow_id}/executions/{execution_id}/cancel` | Cancel a run |
| GET | `/{workflow_id}/executions` | Execution history |

### Nodes — prefix `/api/nodes`
| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | All node type definitions |
| GET | `/{node_type}` | Definition for one node type |

### Versions (prefix `/api`) — `GET|POST /workflows/{id}/versions`, `GET /workflows/{id}/versions/{v}`, `POST /workflows/{id}/versions/{v}/rollback`, `GET /workflows/{id}/versions/diff`

### Replay (prefix `/api`) — `POST /executions/{id}/replay`, `POST /executions/{id}/replay-with-input`

### Compiler (prefix `/api`) — `POST /workflows/{id}/compile`, `GET /workflows/{id}/export`

### Scheduler (prefix `/api`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/workflows/{id}/schedule` | Set/validate cron schedule |
| GET | `/workflows/{id}/schedule` | Current schedule + next run |
| DELETE | `/workflows/{id}/schedule` | Remove schedule |
| GET | `/schedules` | All scheduled workflows |

### Webhooks (prefix `/api`)
| Method | Path | Description |
|--------|------|-------------|
| POST | `/workflows/{id}/webhooks` | Create trigger URL (HMAC secret) |
| GET | `/workflows/{id}/webhooks` | List triggers |
| DELETE | `/webhooks/{webhook_key}` | Remove trigger |
| POST | `/webhooks/{webhook_key}/trigger` | Fire workflow from external services |

### Debug (prefix `/api`) — `POST /executions/{id}/debug`, `POST /executions/{id}/step`, `POST /executions/{id}/resume`, `POST /executions/{id}/breakpoint`, `DELETE /executions/{id}/breakpoint/{node_id}`, `GET /executions/{id}/debug-state`, `DELETE /executions/{id}/debug`

### Credentials (prefix `/api`)
| Method | Path | Description |
|--------|------|-------------|
| POST / GET | `/credentials` | Create / list (names only — never values) |
| GET / PUT / DELETE | `/credentials/{credential_id}` | Manage |
| GET | `/credentials/{credential_id}/decrypt` | Reveal value (rate-limited, `no-store`) |

### WebSocket — `ws://localhost:8000/api/workflows/ws/executions/{execution_id}`
Live execution events (`node_started`, `node_completed`, `node_failed`, `workflow_completed`, …) with token auth and ping/pong keepalive.

## Security

- **Credentials** — encrypted at rest (Fernet); `{{cred:ID}}` placeholders resolved only at run time; **input config and node output are redacted** before being persisted or published (see `app/core/workflow_engine.py`, `app/api/credentials.py`).
- **API keys** — SHA-256 hash + prefix stored; plaintext column removed by migration.
- **Webhooks** — constant-time HMAC secret validation (`hmac.compare_digest`).
- **SSRF** — outbound executor rejects private/link-local/cloud-metadata ranges and non-HTTP schemes.
- **Rate limiting** — Redis-backed sliding window (sorted set per key, accurate across workers/processes) with automatic in-memory fallback when Redis is unavailable (`app/core/rate_limiter.py`).
- **Worker** — idempotency keys, guarded state-machine transitions, clear-on-done, retry backoff + jitter.

## Testing

```bash
DATABASE_URL=sqlite:// .venv/bin/python -m pytest tests/ -q
```

300 test functions in 23 files. Suites touching Redis/Postgres directly (async runtime, worker, timeouts) expect live services; the rest run against SQLite (see `tests/conftest.py`).