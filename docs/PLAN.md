# FlowAlchemy — Implementation Plan & Review Document

**Project:** FlowAlchemy — Visual Workflow Automation Platform
**Frontend:** React + TypeScript + Vite + Tailwind CSS
**Backend:** Python FastAPI + SQLAlchemy + Redis
**Last Updated:** 2026-09-24
**E2E Tests:** 25 test cases + 1 auth setup, all passing (Playwright + Chromium)

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Completed Work — Frontend](#2-completed-work--frontend)
3. [Completed Work — Backend](#3-completed-work--backend)
4. [New Components](#4-new-components)
5. [Modified Files](#5-modified-files)
6. [Known Issues & TODOs](#6-known-issues--todos)
7. [File Index](#7-file-index)

---

## 1. Architecture Overview

### High-Level Flow
```
User Browser
    ↓
React Frontend (Vite, Port 5173)
    ↓ Axios /api/*
FastAPI Backend (Port 8000)
    ↓
PostgreSQL Database + Redis Queue
    ↓
Worker Process → WorkflowEngine → Executors → HTTP/Transform/Condition/Delay/Output
```

### Key Patterns
- **Auth:** JWT tokens stored in localStorage, auto-attached via Axios interceptor
- **Workflows:** React Flow JSON → canonical definition → parallel execution via execution planner
- **Credentials:** AES-256 (Fernet) encrypted, `{{cred:ID}}` placeholder resolution at runtime
- **Real-time:** WebSocket for execution status + polling fallback
- **Theme:** Dark/light via `data-theme` attribute + CSS custom properties + localStorage

---

## 2. Completed Work — Frontend

### 2.1 UI/UX Improvements (Batch 1-10)

| Batch | Feature | Status | Files |
|-------|---------|--------|-------|
| 1 | Auto-save toggle with localStorage sync | ✅ Done | `SettingsPage.tsx` |
| 2 | Dashboard header → avatar dropdown (Settings/Logout) | ✅ Done | `DashboardPage.tsx` |
| 3 | VersionHistory + CredentialsManager as WorkflowPage tabs | ✅ Done | `WorkflowPage.tsx`, `VersionHistory.tsx`, `CredentialsManager.tsx` |
| 4 | WebSocket reconnection (MAX_RETRIES=5, exponential backoff) | ✅ Done | `useExecutionWebSocket.ts` |
| 5 | Auth `User` type + `created_at`, Dashboard "Total Runs" fetch | ✅ Done | `AuthContext.tsx`, `DashboardPage.tsx` |
| 6 | Dashboard stats grid responsive `grid-cols-1 sm:grid-cols-3` | ✅ Done | `DashboardPage.tsx` |
| 7 | `animate-slide-up` keyframes + `.scrollbar-none` utility | ✅ Done | `index.css` |
| 8 | Registration real-time password validation | ✅ Done | `RegisterPage.tsx` |
| 9 | Navigation safety (beforeunload + manual confirm) | ✅ Done | `WorkflowPage.tsx` |
| 10 | `document.title` on every page | ✅ Done | All pages |

### 2.2 Component Improvements

| Feature | Status | Files |
|---------|--------|-------|
| Modal (focus trap, Escape, scroll lock, animations) | ✅ Done | `Modal.tsx` |
| ConfirmDialog (danger/warning/info variants) | ✅ Done | `ConfirmDialog.tsx` |
| Toast notifications (4 types, auto-dismiss, animations) | ✅ Done | `Toast.tsx`, `ToastContext.tsx` |
| Date formatting utilities | ✅ Done | `formatDate.ts` |
| selectedNode stale bug fix (selectedNodeId + useMemo) | ✅ Done | `WorkflowEditor.tsx` |
| isDirty false positive fix (ignore select changes) | ✅ Done | `WorkflowEditor.tsx` |
| Theme flash prevention (inline script in index.html) | ✅ Done | `index.html` |

### 2.3 E2E Test Infrastructure

| Feature | Status | Files |
|---------|--------|-------|
| Auth setup project (login once, save storageState) | ✅ Done | `e2e/auth.setup.ts` |
| Playwright config (setup → chromium dependency) | ✅ Done | `playwright.config.ts` |
| getToken() with module-level caching | ✅ Done | `e2e/flowalchemy.spec.ts` |
| 25 test cases (auth, dashboard, editor, execution, settings, responsive) | ✅ Done | `e2e/flowalchemy.spec.ts` |

---

## 3. Completed Work — Backend

### 3.1 Credential Injection System

| Feature | Status | Files |
|---------|--------|-------|
| `get_credential_value(cred_id, user_id)` helper | ✅ Done | `credentials.py:90-97` |
| `CREDENTIAL_PATTERN` regex for `{{cred:ID}}` | ✅ Done | `workflow_engine.py:18` |
| `_resolve_credentials()` recursive resolver | ✅ Done | `workflow_engine.py:101-119` |
| Credential resolution before node execution | ✅ Done | `workflow_engine.py:121-133` |
| Pass `user_id` from worker to engine | ✅ Done | `worker.py:86` |

### 3.2 Schema Fixes

| Feature | Status | Files |
|---------|--------|-------|
| Condition: +6 operators (greater_equal, less_equal, not_contains, starts_with, ends_with, is_empty, is_not_empty) | ✅ Done | `seed_nodes.py:135` |
| Transform: replace aggregate/custom with identity | ✅ Done | `seed_nodes.py:98` |

---

## 4. New Components

### 4.1 HeadersEditor.tsx
**Path:** `frontend/src/components/HeadersEditor.tsx`
**Lines:** 184

Key-value editor for HTTP headers with:
- Grid-based layout (key input + value input + delete button)
- Quick-add buttons: Content-Type, Authorization, Accept, X-API-Key
- Per-row credential picker (🔒 icon → dropdown → inserts `{{cred:ID}}`)
- Click-outside-to-close pattern for dropdowns

### 4.2 BodyEditor.tsx
**Path:** `frontend/src/components/BodyEditor.tsx`
**Lines:** 150

JSON body editor with:
- Monospace textarea with live JSON validation
- Format button (pretty-print)
- Credential picker button (🔒 icon)
- Validation indicator (green ✓ "Valid JSON" or red error message)

### 4.3 DurationPicker.tsx
**Path:** `frontend/src/components/DurationPicker.tsx`
**Lines:** 71

Duration input with:
- Number input + unit selector (ms, s, m)
- Auto-converts to milliseconds for backend
- Auto-selects most readable unit (e.g., 30000ms → 30s)

### 4.4 TransformParamsEditor.tsx
**Path:** `frontend/src/components/TransformParamsEditor.tsx`
**Lines:** 99

Dynamic form that changes based on selected transform operation:
- `filter` → key + value inputs
- `map` → field input
- `split` → delimiter input
- `merge` → sources JSON textarea
- `identity` → no params needed

### 4.5 Modal.tsx
**Path:** `frontend/src/components/Modal.tsx`
**Lines:** 112

Accessible modal with:
- Focus trap (Tab/Shift+Tab cycles through focusable elements)
- Escape to close
- Body scroll lock
- Backdrop click to close
- Size variants (sm/md/lg)
- ARIA attributes (role="dialog", aria-modal, aria-label)

### 4.6 ConfirmDialog.tsx
**Path:** `frontend/src/components/ConfirmDialog.tsx`
**Lines:** 60

Confirmation dialog built on Modal:
- Variants: danger, warning, info
- Loading spinner during async operations
- Customizable confirm/cancel labels

### 4.7 Toast.tsx + ToastContext.tsx
**Path:** `frontend/src/components/Toast.tsx`, `frontend/src/contexts/ToastContext.tsx`
**Lines:** 64 + 41

Toast notification system:
- Types: success, error, warning, info
- Auto-dismiss (4 seconds default)
- Exit animation before removal
- Position: fixed top-right
- `useToast()` hook for components

---

## 5. Modified Files

### 5.1 NodeConfigForm.tsx (MAJOR REWRITE)
**Path:** `frontend/src/components/NodeConfigForm.tsx`
**Lines:** 401

Changes from generic form to specialized field renderers:

| Field Type | Before | After |
|------------|--------|-------|
| `method` (enum) | Native `<select>` | Custom `MethodSelect` with colored badges |
| `duration_ms`, `timeout` | `<input type="number">` | `DurationPicker` with unit selector |
| `headers` (object) | Raw JSON textarea | `HeadersEditor` key-value grid |
| `body` (object) | Raw JSON textarea | `BodyEditor` with validation + format |
| `params` in transform | Generic object editor | `TransformParamsEditor` dynamic form |
| `url`, `token`, etc. (string) | Plain text input | Text input + credential picker button |

Also includes:
- `MethodSelect` component (lines 42-101) — custom dropdown with colored method badges
- `CREDENTIAL_FIELDS` set — fields where credential picker is available
- `insertCredential()` — cursor-aware `{{cred:ID}}` placeholder insertion

### 5.2 WorkflowEditor.tsx
**Path:** `frontend/src/components/WorkflowEditor.tsx`
**Lines:** 511

Key changes:
- `credentials` state — fetched from `/credentials` API on mount (line 96-98)
- Passes `credentials` to `NodeConfigForm` (line 502)
- `isDirty` fix — filters out `select` type changes (lines 100-110)
- Toast integration for save errors (line 206)

### 5.3 index.html
**Path:** `frontend/index.html`
**Lines:** 19

Added inline script (lines 10-15) to apply theme from localStorage before React mounts, preventing flash of wrong theme.

### 5.4 credentials.py
**Path:** `backend/app/api/credentials.py`
**Lines:** 254

Added `get_credential_value(credential_id, user_id)` helper (lines 90-97) that returns decrypted plaintext for use by the workflow engine.

### 5.5 workflow_engine.py
**Path:** `backend/app/core/workflow_engine.py`
**Lines:** 174

Key changes:
- Import `get_credential_value` (line 13)
- `CREDENTIAL_PATTERN` regex (line 18)
- `user_id` parameter added to `execute()` (line 28)
- `_resolve_credentials()` method (lines 101-119) — recursive placeholder resolution
- Credential resolution in `_execute_node()` (lines 121-133)

### 5.6 worker.py
**Path:** `backend/app/worker.py`
**Lines:** 222

Passes `user_id=execution.user_id` to `engine.execute()` (line 86).

### 5.7 seed_nodes.py
**Path:** `backend/seed_nodes.py`
**Lines:** 250

- Condition operators: 6 → 12 (added `greater_equal`, `less_equal`, `not_contains`, `starts_with`, `ends_with`, `is_empty`, `is_not_empty`)
- Transform operations: `["filter", "map", "aggregate", "merge", "split", "custom"]` → `["identity", "filter", "map", "merge", "split"]`

---

## 6. Known Issues & TODOs

### Critical

| Issue | Location | Description |
|-------|----------|-------------|
| **Encryption salt not persisted — ✅ FIXED** | `credentials.py:61` | `EncryptionService` generates random salt per instance. On server restart, new salt = all encrypted credentials permanently unrecoverable. **Fix:** Derive salt from `settings.SECRET_KEY` or persist in database. **(FIXED — lihat `app/core/encryption.py`, REVIEW-Round4)** |
| **In-memory credential store — ✅ FIXED** | `credentials.py:99` | `_credentials_store` dict loses all data on restart. **Fix:** Move to database table. **(FIXED — DB-backed `credentials` table, migration 007; lihat REVIEW-Round4)** |

### Moderate

| Issue | Location | Description |
|-------|----------|-------------|
| Silent error swallowing — ✅ FIXED | `WorkflowEditor.tsx:97` | `api.get('/credentials').catch(...)` previously swallowed errors silently — now surfaces them via `showToast('error', ...)`. |
| Duplicate credential picker pattern | `HeadersEditor.tsx`, `BodyEditor.tsx`, `NodeConfigForm.tsx` | Same dropdown pattern repeated 3 times — extract to shared `CredentialPicker` component. |

### Minor

| Issue | Location | Description |
|-------|----------|-------------|
| `TransformParamsEditor` useEffect deps | `TransformParamsEditor.tsx:48` | Dependency array is `[operation]` only — intentionally avoids infinite loops but may trigger React lint warnings. |
| `CREDENTIAL_PATTERN.search(str(config))` | `workflow_engine.py:132` | Converts entire config dict to string for matching — inefficient for large configs. Use recursive check instead. |
| E2E test numbering | `flowalchemy.spec.ts` | Test numbering is out of order — responsive tests 14–16 appear after test 20 in the file. Renumbering would improve readability. |
| Fragile E2E selectors | `flowalchemy.spec.ts:475+` | User menu selector `.rounded-full.bg-primary\\/20` is CSS-dependent and may break with style changes. |

---

## 7. File Index

### Frontend — New Files (8)

| File | Lines | Purpose |
|------|-------|---------|
| `src/components/HeadersEditor.tsx` | 184 | Key-value header editor with credential picker |
| `src/components/BodyEditor.tsx` | 150 | JSON body editor with validation + credential picker |
| `src/components/DurationPicker.tsx` | 71 | Duration input with ms/s/m unit conversion |
| `src/components/TransformParamsEditor.tsx` | 99 | Dynamic params form per transform operation |
| `src/components/Modal.tsx` | 112 | Accessible modal with focus trap |
| `src/components/ConfirmDialog.tsx` | 60 | Confirmation dialog (danger/warning/info) |
| `src/components/Toast.tsx` | 64 | Toast notification component |
| `src/contexts/ToastContext.tsx` | 41 | Toast provider + useToast hook |

### Frontend — Modified Files (17)

| File | Lines | Key Changes |
|------|-------|-------------|
| `src/components/NodeConfigForm.tsx` | 401 | Major rewrite: specialized editors, credential picker, MethodSelect |
| `src/components/WorkflowEditor.tsx` | 511 | isDirty fix, credentials fetch, toast integration |
| `src/components/CredentialsManager.tsx` | 198 | Toast + ConfirmDialog integration |
| `src/components/VersionHistory.tsx` | 168 | Toast + ConfirmDialog integration |
| `src/components/ExecutionHistory.tsx` | 145 | formatShortDateTime usage |
| `src/pages/DashboardPage.tsx` | 539 | Modal + ConfirmDialog + Toast, user menu dropdown |
| `src/pages/WorkflowPage.tsx` | 162 | Credentials tab, unsaved changes guard |
| `src/pages/SettingsPage.tsx` | 412 | Theme toggle, auto-save, API key management |
| `src/pages/LoginPage.tsx` | 123 | document.title |
| `src/pages/RegisterPage.tsx` | 265 | Password validation, document.title |
| `src/pages/LandingPage.tsx` | 279 | document.title |
| `src/App.tsx` | 62 | ToastProvider, theme init, settings route |
| `src/index.css` | 325 | Animations, keyframes, theme system |
| `src/lib/formatDate.ts` | 41 | Shared date formatting utilities |
| `src/lib/useExecutionWebSocket.ts` | 123 | Retry/backoff, terminal status tracking |
| `index.html` | 19 | Inline theme script (FOUC prevention) |
| `src/react-flow-overrides.css` | 53 | ReactFlow dark theme overrides |

### Frontend — Test Files (3)

| File | Lines | Purpose |
|------|-------|---------|
| `e2e/flowalchemy.spec.ts` | 597 | 25 E2E test cases (auth, dashboard, editor, execution, settings, responsive) |
| `e2e/auth.setup.ts` | 24 | Auth setup project (login once, save storageState) |
| `playwright.config.ts` | 30 | Two-project config (setup → chromium) |

### Backend — Modified Files (4)

| File | Lines | Key Changes |
|------|-------|-------------|
| `app/api/credentials.py` | 254 | `get_credential_value()` helper |
| `app/core/workflow_engine.py` | 174 | `_resolve_credentials()`, `CREDENTIAL_PATTERN`, `user_id` param |
| `app/worker.py` | 222 | Pass `user_id` to engine |
| `seed_nodes.py` | 250 | Condition +6 operators, Transform operation fix |

### Backend — Unchanged Files (3)

| File | Lines | Why No Changes |
|------|-------|----------------|
| `app/core/executors/http_request.py` | 81 | Receives already-resolved config from engine |
| `app/core/executors/transform.py` | 59 | Receives already-resolved config from engine |
| `app/core/executors/condition.py` | 139 | Receives already-resolved config from engine |

---

## Appendix: Credential Injection Flow

```
1. User creates credential via CredentialsManager
   → POST /api/credentials { name, credential_type, value }
   → Encrypted with AES-256 (Fernet) → stored in the `credentials` DB table (DB-backed, migration 007)

2. User configures HTTP Request node
   → HeadersEditor: {"Authorization": "Bearer {{cred:3}}"}
   → Or BodyEditor: {"token": "{{cred:5}}"}
   → Saved as workflow definition JSON

3. User clicks "Run Workflow"
   → POST /api/workflows/{id}/run → enqueue job → worker picks up

4. Worker calls engine.execute(user_id=execution.user_id)
   → For each node: engine._execute_node()

5. Engine checks for credential patterns
   → CREDENTIAL_PATTERN.search(str(config))
   → If found: engine._resolve_credentials(config, user_id)

6. Resolution walks config recursively
   → Replaces "{{cred:3}}" with get_credential_value(3, user_id)
   → Returns decrypted plaintext

7. Executor receives clean config
   → HttpRequestExecutor: headers = {"Authorization": "Bearer sk-abc123..."}
   → Makes HTTP request with resolved credentials
```

---

## Appendix: E2E Test Coverage

| # | Test | Category |
|---|------|----------|
| 01 | Login page renders correctly | Auth |
| 02 | Register page renders correctly | Auth |
| 03 | Register new account + show API key | Auth |
| 04 | Login error — wrong credentials | Auth |
| 05 | Register error — password mismatch | Auth |
| 06 | Dashboard — empty state | Dashboard |
| 07 | Dashboard — create workflow modal | Dashboard |
| 08 | Dashboard — workflow card | Dashboard |
| 09 | Editor — empty canvas with palette | Editor |
| 10 | Editor — drag node to canvas | Editor |
| 11 | Editor — select node shows properties | Editor |
| 12 | Editor — toolbar states | Editor |
| 13 | History tab — empty state | Editor |
| 14 | Responsive — desktop (1280x800) | Responsive |
| 15 | Responsive — tablet (768x1024) | Responsive |
| 16 | Responsive — mobile (375x812) | Responsive |
| 17 | Run simple workflow via API | Execution |
| 18 | Run workflow from UI | Execution |
| 19 | Run button disabled with no nodes | Execution |
| 20 | Run disconnected graph — allowed | Execution |
| 21 | Settings — page renders with tabs | Settings |
| 22 | Settings — switch tabs | Settings |
| 23 | Settings — change password | Settings |
| 24 | Settings — preferences save | Settings |
| 25 | Settings — back to dashboard | Settings |

**Total: 26 tests (1 setup + 25 test cases)**

---

## Appendix: Animation System

| Animation | Class | Duration | Usage |
|-----------|-------|----------|-------|
| Fade in | `.animate-fade-in` | 0.4s | Page transitions, list items |
| Fade in up | `.animate-fade-in-up` | 0.5s | Cards, content sections |
| Slide in right | `.animate-slide-in-right` | 0.4s | Properties panel |
| Slide in left | `.animate-slide-in-left` | 0.4s | Sidebars |
| Scale in | `.animate-scale-in` | 0.3s | Modals, dropdowns |
| Shake | `.animate-shake` | 0.5s | Error messages |
| Pulse slow | `.animate-pulse-slow` | 2s | Loading indicators |
| Float | `.animate-float` | 3s | Decorative elements |
| Slide up | `.animate-slide-up` | 0.3s | Slide-up panels |
| Modal backdrop | `.animate-modal-backdrop` | 0.2s | Modal overlay |
| Modal card | `.animate-modal-card` | 0.25s | Modal content |
| Toast in | `.animate-toast-in` | 0.3s | Toast entry |
| Toast out | `.animate-toast-out` | 0.3s | Toast exit |
| Stagger children | `.stagger-children > *` | 0.5s + delays | Sequential list items |
