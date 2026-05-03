#!/usr/bin/env bash
# setup_vercel.sh — links repo to Vercel project, sets env vars, prints preview URL.
# Usage: bash infra/setup_vercel.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${REPO_ROOT}/.env"

if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  set -a; source "$ENV_FILE"; set +a
fi

: "${VERCEL_TOKEN:?VERCEL_TOKEN must be set in .env}"

# Require the Vercel CLI
if ! command -v vercel &>/dev/null; then
  echo "[setup_vercel] Vercel CLI not found. Installing via npm..."
  npm install -g vercel
fi

echo "[setup_vercel] Linking repository to Vercel project..."
cd "$REPO_ROOT"

# Link (non-interactive): use org/project IDs if already known
if [[ -n "${VERCEL_ORG_ID:-}" && -n "${VERCEL_PROJECT_ID:-}" ]]; then
  VERCEL_ORG_ID="$VERCEL_ORG_ID" VERCEL_PROJECT_ID="$VERCEL_PROJECT_ID" \
    vercel link --token "$VERCEL_TOKEN" --yes
else
  vercel link --token "$VERCEL_TOKEN" --yes
fi

# Push env vars to Vercel (preview + production)
if [[ -f "$ENV_FILE" ]]; then
  echo "[setup_vercel] Pushing env vars to Vercel preview and production environments..."
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ -z "${line// }" ]] && continue
    key="${line%%=*}"
    value="${line#*=}"
    # Add to both preview and production; ignore errors for already-existing keys
    echo "$value" | vercel env add "$key" preview  --token "$VERCEL_TOKEN" --yes 2>/dev/null || true
    echo "$value" | vercel env add "$key" production --token "$VERCEL_TOKEN" --yes 2>/dev/null || true
  done < "$ENV_FILE"
  echo "[setup_vercel] Env vars pushed."
fi

# Deploy to get a preview URL
echo "[setup_vercel] Triggering preview deployment..."
PREVIEW_URL=$(vercel deploy --token "$VERCEL_TOKEN" 2>&1 | grep -oP 'https://[^\s]+\.vercel\.app' | tail -1 || echo "${VERCEL_PREVIEW_URL:-not-yet-deployed}")
echo "[setup_vercel] Preview URL: $PREVIEW_URL"
echo "[setup_vercel] Done."
