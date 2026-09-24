# FlowAlchemy

> **Visual workflow automation engine** — a drag-and-drop workflow builder whose graphs compile to executable Python. Think Zapier-style automation with a developer-grade edge: versioning, replay, scheduling, webhooks, a visual debugger, and encrypted credential management.

![Status](https://img.shields.io/badge/status-active-22d3ee) ![License](https://img.shields.io/badge/license-MIT-7c3aed)

---

## ✨ Features

| Area | Feature | Status |
|------|---------|--------|
| **Visual builder** | Drag-and-drop canvas (React Flow), node palette, real-time execution preview via WebSocket | ✅ UI + API |
| **Data flow** | Node inputs auto-resolved from `trigger_data` + upstream outputs; `{{path.to.field}}` templates injected into `config.data` | ✅ |
| **Branching** | Conditional edges — only nodes whose incoming condition is satisfied run; others are marked `skipped` in history | ✅ |
| **Execution history** | Per-node breakdown (status, duration, output, errors incl. skipped) persisted to DB, inspectable via `GET /api/workflows/executions/{id}/nodes` and expandable "Detail" rows in the UI | ✅ UI + API |
| **Executors** | HTTP request, transform, condition, delay, output, trigger nodes | ✅ |
| **Versioning** | Every save snapshots a version; compare any two versions side-by-side and roll back | ✅ UI + API |
| **Replay** | Re-run an execution with the same or modified input, then compare runs | ✅ API (UI in roadmap) |
| **Python compiler** | Compile a workflow graph into a standalone, executable Python script and download it | ✅ API (UI in roadmap) |
| **Scheduling** | Cron-based schedules (validated, minimum 5-min interval); worker picks up due runs | ✅ API (UI in roadmap) |
| **Webhooks** | Public trigger URLs with HMAC-signed secrets to fire workflows from external services | ✅ API (UI in roadmap) |
| **Visual debugger** | Breakpoints, step / resume / pause over WebSocket, live variable inspection | ✅ UI + API |
| **Credentials** | AES-(Fernet)-encrypted secrets, injected via `{{cred:ID}}` placeholders, auto-redacted from execution history | ✅ UI + API |
| **Runtime safety** | SSRF protection, rate limiting, per-user/per-total concurrency limits, node & workflow timeouts, retries with exponential backoff + jitter, idempotent worker, state machine | ✅ |

## 🧰 Tech Stack

| Layer | Technologies |
|-------|--------------|
| **Frontend** | React 19, TypeScript, Vite, Tailwind CSS 4, React Flow (@xyflow/react), React Router 7, Axios, Playwright (E2E) |
| **Backend** | Python 3.10+, FastAPI, SQLAlchemy 2, Pydantic 2, Alembic, Redis (queue/pub-sub), structlog |
| **Infra** | Docker Compose (PostgreSQL 16, Redis 7, nginx), multi-stage Dockerfiles |

## 🏗️ Architecture

```
┌──────────────────────────────┐        ┌─────────────────────────────────────┐
│  Frontend (React + nginx)    │        │  FastAPI Backend          Worker     │
│  Visual editor · dashboard   │◄──────►│  REST /api · WebSocket    (poll)     │
└──────────────────────────────┘  HTTP   └──────────────┬──────────────────────┘
        /api proxied to :8000             WS events     │  enqueue jobs
                                                       ▼
                                          ┌──────────────────────────────┐
                                          │   PostgreSQL    Redis         │
                                          │  (workflows,         (queue,   │
                                          │   executions,        pub/sub,  │
                                          │   credentials)      rate-limit)│
                                          └──────────────────────────────┘
```

- The **frontend** sends a workflow execution; the **backend** validates the graph, enqueues the job in Redis, and the **worker** executes it through the workflow engine.
- The engine resolves each node's input from **trigger data + every upstream node's output**, expands `{{path.to.field}}` templates, and injects the result into the node's `config.data` — so condition, transform, delay, and output nodes operate on real upstream values.
- **Conditional edges** gate execution: a node runs when at least one incoming edge's condition is satisfied; unsatisfied downstream nodes are marked `skipped` (persisted and streamed over WebSocket).
- Execution progress (node started / completed / failed / skipped) streams back to the UI over **WebSocket**, with an automatic polling fallback.
- Credentials are stored **encrypted** (`Fernet`), resolved at execution time, and **redacted** from both config and node output before anything is persisted or pushed over the wire.

## 🚀 Quick Start

### Option A — Docker (recommended)

```bash
cp .env.example .env
# Generate real secrets (compose fails fast if these are left as REPLACE_ME):
openssl rand -hex 32   # → SECRET_KEY
openssl rand -hex 16   # → POSTGRES_PASSWORD

docker compose up --build
```

- Frontend: http://localhost:80
- API docs (Swagger UI): http://localhost:8000/docs
- Health check: http://localhost:8000/health

> Migrations run automatically on container start (`alembic upgrade head` in the entrypoint). PostgreSQL binds to `127.0.0.1:5433` and Redis to `127.0.0.1:6379` here for local development.

### Option B — Local development

**Backend** (requires PostgreSQL + Redis running, e.g. `docker compose up postgres redis`):

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # set SECRET_KEY, DATABASE_URL, REDIS_URL
alembic upgrade head        # apply migrations
python run.py               # uvicorn API on :8000 (reload on)
python -m app.worker        # separate terminal: job worker
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev                 # Vite dev server on :5173 (proxies /api → :8000)
```

## 📸 Screenshots

| | |
|---|---|
| ![Login](screenshots/01_Login_page_renders_correctly.png) | ![Editor canvas](screenshots/09_Editor_empty_canvas.png) |
| ![Workflow card](screenshots/08_Dashboard_workflow_card.png) | ![Node properties](screenshots/11_Editor_select_node_shows_properties.png) |
| ![Execution history](screenshots/13_History_tab_empty_state.png) | ![Mobile responsive](screenshots/16_Responsive_mobile_375x812.png) |

Full gallery: `screenshots/` (20 captures covering auth, dashboard, editor, history, and responsive layouts).

## 🧪 Testing

```bash
# Backend — unit & integration (SQLite; some suites require live Redis/Postgres)
cd backend && DATABASE_URL=sqlite:// .venv/bin/python -m pytest tests/ -q

# Frontend — Playwright E2E (backend must be running)
cd frontend && npx playwright test
```

- **300 backend test functions** across 23 test files (graph validation, execution engine, condition/transform/delay executors, retry/backoff, timeouts & cancellation, scheduler, webhooks/HMAC, versioning, replay, credentials & encryption, SSRF, state machine, worker idempotency).
- **25 Playwright E2E tests** covering auth, dashboard, editor, and settings — with 20 auto-captured screenshots.

## 🗂️ Project Structure

```
flow-alchemy/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI routers (auth, workflows, versions, replay,
│   │   │                 #   compiler, scheduler, webhooks, debug, credentials, ws)
│   │   ├── core/         # engine, executors, planner, queue, security,
│   │   │                 #   encryption, ssrf_protection, rate_limiter, state_machine
│   │   ├── models/       # SQLAlchemy models
│   │   ├── schemas/      # Pydantic schemas
│   │   └── services/     # scheduler, webhook, execution-state services
│   ├── alembic/          # migrations (001–009 + security fixes)
│   ├── tests/            # 23 test files
│   └── Dockerfile / entrypoint.sh
├── frontend/
│   ├── src/
│   │   ├── components/   # WorkflowEditor, NodePalette, VisualDebugger, Modals…
│   │   ├── pages/        # Landing, Login, Register, Dashboard, Workflow, Settings
│   │   ├── hooks/ · lib/ · contexts/
│   └── e2e/              # Playwright specs
├── docker-compose.yml    # postgres + redis + backend + worker + frontend
└── screenshots/          # E2E capture gallery
```

## 🔒 Security Notes

- **Credentials**: encrypted at rest (Fernet), key derived deterministically from `SECRET_KEY`; stored in DB (not process memory); never returned by list/get APIs; `{{cred:ID}}` placeholders are resolved only at run time and **redacted** from both input config and node output before persistence/events.
- **API keys**: stored as SHA-256 hash + prefix — plaintext column dropped via migration.
- **Webhooks**: secrets validated with constant-time `hmac.compare_digest`.
- **SSRF**: outbound HTTP executor blocks private/link-local/cloud-metadata ranges and non-HTTP schemes.
- **CORS**: explicit allow-list of origins (no wildcard).
- **Runtime**: per-user + global concurrency limits, payload/response size caps, node & workflow timeouts, workflow-level retries with jitter.

## 📚 API Overview

Swagger UI at `http://localhost:8000/docs`. WebSocket: `ws://localhost:8000/api/workflows/ws/executions/{execution_id}` (event stream + ping/pong).

| Resource | Endpoints |
|----------|-----------|
| **Auth** | `POST /api/auth/register` · `POST /api/auth/login` · `GET|PUT /api/auth/me` · `POST /api/auth/change-password` · `POST /api/auth/regenerate-api-key` |
| **Workflows** | `GET|POST /api/workflows` · `GET|PUT|DELETE /api/workflows/{id}` · `POST /api/workflows/{id}/run` · `POST /api/workflows/{id}/executions/{eid}/cancel` · `GET /api/workflows/{id}/executions` · `GET /api/workflows/executions/{eid}/nodes` (per-node history) |
| **Nodes** | `GET /api/nodes` · `GET /api/nodes/{type}` |
| **Versions** | `GET|POST /api/workflows/{id}/versions` · `GET /api/workflows/{id}/versions/{v}` · `POST .../versions/{v}/rollback` · `GET .../versions/diff` |
| **Replay** | `POST /api/executions/{id}/replay` · `POST /api/executions/{id}/replay-with-input` |
| **Compiler** | `POST /api/workflows/{id}/compile` · `GET /api/workflows/{id}/export` |
| **Scheduler** | `POST|GET|DELETE /api/workflows/{id}/schedule` · `GET /api/schedules` |
| **Webhooks** | `POST|GET /api/workflows/{id}/webhooks` · `DELETE /api/webhooks/{key}` · `POST /api/webhooks/{key}/trigger` |
| **Debug** | `POST /api/executions/{id}/debug` · `POST .../step|resume` · `POST|DELETE .../breakpoint` · `GET .../debug-state` |
| **Credentials** | `POST|GET /api/credentials` · `GET|PUT|DELETE /api/credentials/{id}` · `GET /api/credentials/{id}/decrypt` (rate-limited) |

## 🗺️ Roadmap

- Frontend UI for scheduler, webhooks, replay & Python-export (API layer is complete and tested)
- Redis-backed global rate limiting; stronger DNS-rebinding protection for SSRF guard
- Fuzzy / advanced condition expressions in the visual editor UI (engine already supports full expressions)

## 📄 License

MIT