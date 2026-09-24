#!/bin/sh
# FlowAlchemy backend entrypoint — runs DB migrations before startup.
# Used by BOTH backend and worker (same image, `build: ./backend`),
# so migration logic lives here exactly once (single-source policy).
set -e

# Retry guard: backend + worker boot concurrently and both run
# `alembic upgrade head`. Alembic/Postgres serializes DDL via locks,
# so the loser fails fast — retry with backoff until it succeeds.
# Also covers "DB container up but not yet accepting connections".
MAX_RETRIES="${MIGRATION_MAX_RETRIES:-30}"
SLEEP_SECS="${MIGRATION_RETRY_INTERVAL:-2}"

attempt=1
until alembic upgrade head; do
  if [ "$attempt" -ge "$MAX_RETRIES" ]; then
    echo "ERROR: 'alembic upgrade head' failed after ${attempt} attempts. Giving up." >&2
    exit 1
  fi
  echo "Migration attempt ${attempt}/${MAX_RETRIES} failed, retrying in ${SLEEP_SECS}s..." >&2
  attempt=$((attempt + 1))
  sleep "$SLEEP_SECS"
done

echo "Migrations up to date. Starting: $*"
exec "$@"
