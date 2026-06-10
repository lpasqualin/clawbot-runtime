#!/bin/bash
# memory_write.sh — governed MEMORY.md write wrapper
# Usage: memory_write.sh <content_file>
# content_file must be a validated replacement for MEMORY.md

set -euo pipefail

MEMORY_PATH="/home/clawbot/.openclaw/workspace/MEMORY.md"
LOCK_FILE="/tmp/memory_write.lock"
CONTENT_FILE="${1:-}"

if [[ -z "$CONTENT_FILE" || ! -f "$CONTENT_FILE" ]]; then
  echo "ERROR: content_file required and must exist" >&2
  exit 1
fi

# Emergency override
if [[ "${ALLOW_MEMORY_EMERGENCY_WRITE:-0}" == "1" ]]; then
  echo "WARNING: EMERGENCY WRITE OVERRIDE ACTIVE — logging and proceeding" >&2
  echo "{\"ts\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"actor\":\"emergency_override\",\"op\":\"emergency_write\",\"note\":\"ALLOW_MEMORY_EMERGENCY_WRITE=1\"}" \
    >> /home/clawbot/.openclaw/workspace/memory_journal.jsonl
fi

(
  flock -x 200

  # Validate content file is non-empty
  if [[ ! -s "$CONTENT_FILE" ]]; then
    echo "ERROR: content_file is empty" >&2
    exit 1
  fi

  cp "$CONTENT_FILE" "$MEMORY_PATH"

  # Git commit
  cd /home/clawbot/.openclaw/workspace
  git add MEMORY.md
  if [[ -f memory_journal.jsonl ]]; then
    git add memory_journal.jsonl
  fi
  git diff --cached --quiet || git commit -m "memory: governed write $(date -u +%Y-%m-%dT%H:%M:%SZ)"

) 200>"$LOCK_FILE"

echo "MEMORY.md updated and committed."
