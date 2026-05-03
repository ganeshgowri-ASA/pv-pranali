-- pv-pranali schema: idempotent Supabase migration.
-- Run with: psql $DATABASE_URL -f infra/migrations/0001_init.sql

-- ---------------------------------------------------------------------------
-- Extensions
-- ---------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS vector;

-- ---------------------------------------------------------------------------
-- Shared trigger function: keeps updated_at current on every UPDATE
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION _set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

-- ---------------------------------------------------------------------------
-- projects
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS projects (
    id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name       TEXT        NOT NULL,
    intent     TEXT        NOT NULL,
    status     TEXT        NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'trg_projects_updated_at'
    ) THEN
        CREATE TRIGGER trg_projects_updated_at
            BEFORE UPDATE ON projects
            FOR EACH ROW EXECUTE FUNCTION _set_updated_at();
    END IF;
END $$;

-- ---------------------------------------------------------------------------
-- pipeline_runs
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id  UUID        NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    status      TEXT        NOT NULL DEFAULT 'running',
    current_node TEXT,
    token_count INTEGER     NOT NULL DEFAULT 0,
    started_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'trg_pipeline_runs_updated_at'
    ) THEN
        CREATE TRIGGER trg_pipeline_runs_updated_at
            BEFORE UPDATE ON pipeline_runs
            FOR EACH ROW EXECUTE FUNCTION _set_updated_at();
    END IF;
END $$;

-- ---------------------------------------------------------------------------
-- gate_events
-- One row per gate per run. status: pending | approved | rejected
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS gate_events (
    id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id     UUID        NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,
    gate_name  TEXT        NOT NULL,
    status     TEXT        NOT NULL DEFAULT 'pending',
    reason     TEXT,
    operator   TEXT,
    decided_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'trg_gate_events_updated_at'
    ) THEN
        CREATE TRIGGER trg_gate_events_updated_at
            BEFORE UPDATE ON gate_events
            FOR EACH ROW EXECUTE FUNCTION _set_updated_at();
    END IF;
END $$;

-- ---------------------------------------------------------------------------
-- bom_items
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS bom_items (
    id             UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id         UUID          NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,
    reference      TEXT          NOT NULL,
    description    TEXT          NOT NULL,
    quantity       INTEGER       NOT NULL DEFAULT 1,
    unit_price_inr NUMERIC(12,4),
    supplier       TEXT,
    part_number    TEXT,
    lead_time_days INTEGER,
    frozen         BOOLEAN       NOT NULL DEFAULT false,
    created_at     TIMESTAMPTZ   NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ   NOT NULL DEFAULT now()
);

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'trg_bom_items_updated_at'
    ) THEN
        CREATE TRIGGER trg_bom_items_updated_at
            BEFORE UPDATE ON bom_items
            FOR EACH ROW EXECUTE FUNCTION _set_updated_at();
    END IF;
END $$;

-- ---------------------------------------------------------------------------
-- risk_register
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS risk_register (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id      UUID        NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,
    category    TEXT        NOT NULL,
    description TEXT        NOT NULL,
    likelihood  SMALLINT    CHECK (likelihood BETWEEN 1 AND 5),
    impact      SMALLINT    CHECK (impact BETWEEN 1 AND 5),
    mitigation  TEXT,
    owner       TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'trg_risk_register_updated_at'
    ) THEN
        CREATE TRIGGER trg_risk_register_updated_at
            BEFORE UPDATE ON risk_register
            FOR EACH ROW EXECUTE FUNCTION _set_updated_at();
    END IF;
END $$;

-- ---------------------------------------------------------------------------
-- rfq_drafts
-- status: draft | sent | acknowledged
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS rfq_drafts (
    id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id         UUID        NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,
    supplier_name  TEXT        NOT NULL,
    supplier_email TEXT,
    subject        TEXT        NOT NULL,
    body_text      TEXT        NOT NULL,
    sent_at        TIMESTAMPTZ,
    status         TEXT        NOT NULL DEFAULT 'draft',
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger WHERE tgname = 'trg_rfq_drafts_updated_at'
    ) THEN
        CREATE TRIGGER trg_rfq_drafts_updated_at
            BEFORE UPDATE ON rfq_drafts
            FOR EACH ROW EXECUTE FUNCTION _set_updated_at();
    END IF;
END $$;
