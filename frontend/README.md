# FlowAlchemy — Frontend

React 19 + TypeScript + Vite + Tailwind CSS 4 + React Flow web client for the FlowAlchemy workflow automation engine.

## Stack

- **React 19** + **TypeScript** (strict, `verbatimModuleSyntax`)
- **Vite 8** with the official React + Tailwind v4 plugins
- **@xyflow/react** (React Flow 12) — visual workflow canvas with custom nodes
- **React Router 7**, **Axios**, **lucide-react** icons
- **Playwright** for E2E (25 specs, auto-captured screenshots)

## Getting started

The backend must be running (see the root `README.md`).

```bash
npm install
npm run dev        # Vite dev server on http://localhost:5173
```

`vite.config.ts` proxies `/api` → `http://localhost:8000`, so the frontend talks to the backend through the same origin in development.

### Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `VITE_API_BASE_URL` | `/api` | Base path for all API calls (same-origin proxy in dev) |

Copy `frontend/.env.example` → `frontend/.env` only if you need to override the API base.

## Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Vite dev server with HMR |
| `npm run build` | `tsc -b && vite build` (type-check + production bundle) |
| `npm run lint` | Oxlint |
| `npm run preview` | Preview the production build locally |

## E2E tests

```bash
npx playwright test            # full suite
npx playwright test --ui       # interactive UI runner
npx playwright show-report     # HTML report after a run
```

`e2e/auth.setup.ts` authenticates once and reuses the session for the rest of the suite (`storageState`). Screenshots are written to the `screenshots/` folder in the repo root.

## Project structure

```
src/
├── components/     # WorkflowEditor, NodePalette, CustomNode, NodeConfigForm,
│                   #   VisualDebugger, CredentialsManager, CredentialPicker,
│                   #   VersionHistory, VersionDiff, ExecutionHistory, Modal, Toast…
├── pages/          # Landing, Login, Register, Dashboard, Workflow, Settings
├── hooks/          # e.g. useCredentialPicker
├── lib/            # api client, WebSocket hook, date formatting
├── contexts/       # AuthContext, ToastContext
└── index.css       # Tailwind v4 theme tokens (light/dark via [data-theme])
```