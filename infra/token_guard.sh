#!/usr/bin/env bash
# Hard token cap enforcer. Usage: bash infra/token_guard.sh <SESSION_ID> <CAP>
# Writes blockers/<SESSION_ID>.md and exits 0 when cap is reached.
set -euo pipefail

SESSION_ID="${1:-unknown}"
TOKEN_CAP="${2:-50000}"
COUNTER_FILE="/tmp/pp_tokens_${SESSION_ID}"

[[ -f "$COUNTER_FILE" ]] || echo 0 > "$COUNTER_FILE"

current=$(cat "$COUNTER_FILE")

if (( current >= TOKEN_CAP )); then
  echo "[token_guard] Session ${SESSION_ID}: cap ${TOKEN_CAP} reached (used: ${current}). Writing blocker." >&2
  mkdir -p blockers
  printf 'Token cap %s reached for session %s (used: %s).\n' \
    "$TOKEN_CAP" "$SESSION_ID" "$current" > "blockers/${SESSION_ID}.md"
  exit 0
fi

echo "[token_guard] Session ${SESSION_ID}: used=${current}, cap=${TOKEN_CAP}. OK."
