#!/usr/bin/env bash
# setup_railway.sh — provisions Railway project, sets env vars from .env, prints deploy URL.
# Usage: bash infra/setup_railway.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/../.env"

if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  set -a; source "$ENV_FILE"; set +a
fi

: "${RAILWAY_TOKEN:?RAILWAY_TOKEN must be set in .env}"

# Require the Railway CLI
if ! command -v railway &>/dev/null; then
  echo "[setup_railway] Railway CLI not found. Installing via npm..."
  npm install -g @railway/cli
fi

echo "[setup_railway] Authenticating with Railway..."
RAILWAY_TOKEN="$RAILWAY_TOKEN" railway whoami

# Create or link project
if [[ -z "${RAILWAY_PROJECT_ID:-}" ]]; then
  echo "[setup_railway] No RAILWAY_PROJECT_ID set — creating new project 'pv-pranali'..."
  RAILWAY_TOKEN="$RAILWAY_TOKEN" railway init --name pv-pranali --no-input
else
  echo "[setup_railway] Linking existing project $RAILWAY_PROJECT_ID..."
  RAILWAY_TOKEN="$RAILWAY_TOKEN" railway link "$RAILWAY_PROJECT_ID"
fi

# Propagate all .env keys to Railway environment
if [[ -f "$ENV_FILE" ]]; then
  echo "[setup_railway] Pushing env vars from .env to Railway..."
  while IFS= read -r line || [[ -n "$line" ]]; do
    # Skip comments and empty lines
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ -z "${line// }" ]] && continue
    key="${line%%=*}"
    value="${line#*=}"
    RAILWAY_TOKEN="$RAILWAY_TOKEN" railway variables set "${key}=${value}" --environment "${RAILWAY_ENVIRONMENT:-production}" 2>/dev/null || true
  done < "$ENV_FILE"
  echo "[setup_railway] Env vars pushed."
fi

# Retrieve and print deploy URL
DEPLOY_URL=$(RAILWAY_TOKEN="$RAILWAY_TOKEN" railway status --json 2>/dev/null | grep -oP '"url":"\K[^"]+' | head -1 || echo "${RAILWAY_DEPLOY_URL:-not-yet-deployed}")
echo "[setup_railway] Deploy URL: $DEPLOY_URL"
echo "[setup_railway] Done."
