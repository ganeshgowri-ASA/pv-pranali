#!/usr/bin/env bash
# check_env.sh — reads .env, asserts all required keys are non-empty.
# Exits 0 if all present; exits 1 and prints missing key names if any absent.
# Usage: bash infra/check_env.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/../.env"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "[check_env] ERROR: .env not found at $ENV_FILE"
  echo "[check_env] Copy .env.example to .env and fill in real values."
  exit 1
fi

# shellcheck disable=SC1090
set -a; source "$ENV_FILE"; set +a

# Full list of required keys (all service groups)
REQUIRED_KEYS=(
  # MiMo
  MIMO_API_KEY
  MIMO_BASE_URL
  # Supabase
  SUPABASE_URL
  SUPABASE_ANON_KEY
  SUPABASE_SERVICE_ROLE_KEY
  SUPABASE_DB_URL
  # Railway
  RAILWAY_TOKEN
  # Vercel
  VERCEL_TOKEN
  # Mouser
  MOUSER_API_KEY
  # DigiKey
  DIGIKEY_CLIENT_ID
  DIGIKEY_CLIENT_SECRET
  # Unipile
  UNIPILE_DSN
  # GitHub
  GITHUB_TOKEN
)

MISSING=()
for key in "${REQUIRED_KEYS[@]}"; do
  val="${!key:-}"
  if [[ -z "$val" ]]; then
    MISSING+=("$key")
  fi
done

if [[ ${#MISSING[@]} -gt 0 ]]; then
  echo "[check_env] FAIL — missing or empty keys:"
  for k in "${MISSING[@]}"; do
    echo "  - $k"
  done
  exit 1
fi

echo "[check_env] OK — all ${#REQUIRED_KEYS[@]} required keys are set."
