#!/usr/bin/env bash
# setup_supabase.sh — creates PV-Pranali schema, enables pgvector, prints connection string.
# Usage: bash infra/setup_supabase.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/../.env"

if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  set -a; source "$ENV_FILE"; set +a
fi

: "${SUPABASE_DB_URL:?SUPABASE_DB_URL must be set in .env}"

echo "[setup_supabase] Connecting to Supabase Postgres..."

# Enable pgvector extension
psql "$SUPABASE_DB_URL" <<'SQL'
CREATE EXTENSION IF NOT EXISTS vector;
SQL
echo "[setup_supabase] pgvector enabled."

# Create application schema
psql "$SUPABASE_DB_URL" <<'SQL'
-- Proposals table: one row per customer proposal run
CREATE TABLE IF NOT EXISTS proposals (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  intent      TEXT NOT NULL,
  status      TEXT NOT NULL DEFAULT 'pending',
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Gates table: HITL approval checkpoints
CREATE TABLE IF NOT EXISTS gates (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  proposal_id   UUID REFERENCES proposals(id) ON DELETE CASCADE,
  gate_name     TEXT NOT NULL,   -- bom_freeze | pcb_drc | rfq_send | public_post | customer_send
  status        TEXT NOT NULL DEFAULT 'pending', -- pending | approved | rejected
  approved_by   TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- BoMs table: bill-of-materials line items
CREATE TABLE IF NOT EXISTS boms (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  proposal_id   UUID REFERENCES proposals(id) ON DELETE CASCADE,
  mpn           TEXT NOT NULL,
  description   TEXT,
  qty           INTEGER NOT NULL DEFAULT 1,
  unit_price_inr NUMERIC(12,4),
  supplier      TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Suppliers table: RFQ targets
CREATE TABLE IF NOT EXISTS suppliers (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name        TEXT NOT NULL,
  contact_url TEXT,
  api_source  TEXT,   -- mouser | digikey | element14 | robu | rs
  country     TEXT DEFAULT 'IN',
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Runs table: agent execution log
CREATE TABLE IF NOT EXISTS runs (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  proposal_id UUID REFERENCES proposals(id) ON DELETE CASCADE,
  agent       TEXT NOT NULL,
  tokens_used INTEGER DEFAULT 0,
  status      TEXT NOT NULL DEFAULT 'running',
  started_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  ended_at    TIMESTAMPTZ
);

-- Docs table: generated output artefacts (DOCX/PDF/PPTX)
CREATE TABLE IF NOT EXISTS docs (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  proposal_id UUID REFERENCES proposals(id) ON DELETE CASCADE,
  doc_type    TEXT NOT NULL,   -- bom | proposal | pitch | landing | linkedin
  storage_path TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Embeddings table: pgvector RAG store
CREATE TABLE IF NOT EXISTS embeddings (
  id          BIGSERIAL PRIMARY KEY,
  proposal_id UUID REFERENCES proposals(id) ON DELETE CASCADE,
  content     TEXT NOT NULL,
  embedding   vector(1536),
  metadata    JSONB,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for fast ANN similarity search
CREATE INDEX IF NOT EXISTS embeddings_embedding_idx
  ON embeddings USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);
SQL
echo "[setup_supabase] Schema created (proposals, gates, boms, suppliers, runs, docs, embeddings)."

echo "[setup_supabase] Connection string: $SUPABASE_DB_URL"
echo "[setup_supabase] Done."
