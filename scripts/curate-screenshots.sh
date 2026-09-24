#!/usr/bin/env bash
set -euo pipefail

SRC_DIR="frontend/e2e/screenshots"
DEST_DIR="docs/images"

# Remove stale files from docs/images
if [ -d "$DEST_DIR" ]; then
  rm -rf "${DEST_DIR:?}/"*
fi

# Copy all screenshots
mkdir -p "$DEST_DIR"
cp -r "$SRC_DIR"/. "$DEST_DIR"/

# Count files
FILE_COUNT=$(find "$DEST_DIR" -type f | wc -l | tr -d ' ')
echo "Curated $FILE_COUNT screenshot(s) into $DEST_DIR/"

# Warn about key exposure
if [ -f "$DEST_DIR/auth/04-register-success.png" ]; then
  echo "⚠️  WARNING: auth/04-register-success.png exists — verify API key is masked in the UI before publishing."
fi
