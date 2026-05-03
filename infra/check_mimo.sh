#!/usr/bin/env bash
# MiMo endpoint health-check: 1-token round-trip latency probe.
# Reads MIMO_API_KEY and MIMO_BASE_URL from .env in the repo root.
# Exits 0 on HTTP 200, 1 on any failure.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/../.env"

if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  set -o allexport
  source "$ENV_FILE"
  set +o allexport
fi

if [[ -z "${MIMO_API_KEY:-}" ]]; then
  echo "ERROR: MIMO_API_KEY is not set" >&2
  exit 1
fi

if [[ -z "${MIMO_BASE_URL:-}" ]]; then
  echo "ERROR: MIMO_BASE_URL is not set" >&2
  exit 1
fi

REQUEST_URL="${MIMO_BASE_URL%/}/v1/chat/completions"

PAYLOAD='{
  "model": "mimo",
  "messages": [{"role": "user", "content": "Hi"}],
  "max_tokens": 1,
  "temperature": 0
}'

START_NS=$(date +%s%N 2>/dev/null || python3 -c 'import time; print(int(time.time()*1e9))')

HTTP_RESPONSE=$(curl -s -w "\n%{http_code}" \
  -X POST "$REQUEST_URL" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${MIMO_API_KEY}" \
  --max-time 30 \
  -d "$PAYLOAD" 2>/dev/null) || {
    echo "ERROR: curl failed — endpoint unreachable: $REQUEST_URL" >&2
    exit 1
  }

END_NS=$(date +%s%N 2>/dev/null || python3 -c 'import time; print(int(time.time()*1e9))')

BODY=$(echo "$HTTP_RESPONSE" | head -n -1)
HTTP_STATUS=$(echo "$HTTP_RESPONSE" | tail -n 1)
LATENCY_MS=$(( (END_NS - START_NS) / 1000000 ))

echo "HTTP status : ${HTTP_STATUS}"
echo "Latency (ms): ${LATENCY_MS}"

if [[ "$HTTP_STATUS" != "200" ]]; then
  echo "ERROR: non-200 response" >&2
  echo "Response body: ${BODY}" >&2
  exit 1
fi

FIRST_TOKEN=$(echo "$BODY" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    token = data['choices'][0]['message']['content']
    print('First token :', repr(token))
except Exception as e:
    print('WARN: could not parse first token:', e, file=sys.stderr)
" 2>&1)

echo "$FIRST_TOKEN"

GIT_SHA=$(git -C "$SCRIPT_DIR" rev-parse --short HEAD 2>/dev/null || echo "unknown")
echo "0.3 OK ${GIT_SHA}" >> /tmp/pp_mimo.log

echo "check_mimo: OK"
exit 0
