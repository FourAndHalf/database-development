-- ============================================================
-- Eval / Golden Dataset Schema (PostgreSQL)
-- Adds: eval_dataset, golden_record, eval_run, eval_result
-- Adapted from ai/governance/golden_dataset.md Phase 4 to match
-- this repo's conventions (uuid PKs via pgcrypto, text chunk ids
-- matching chunks.id from scripts/schema.sql).
-- NOT applied automatically — run manually against nexus_db:
--   docker exec -i nexus-pg psql -U nexus -d nexus_db -f eval/dataset/migrations/001_eval_schema.sql
-- ============================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TYPE eval_unit  AS ENUM ('component', 'task');
CREATE TYPE eval_split AS ENUM ('dev', 'holdout');

-- ---------- versioned dataset container ----------
CREATE TABLE eval_dataset (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  version     text NOT NULL UNIQUE,     -- 'v1', 'v2' — bump on any label change
  created_at  timestamptz NOT NULL DEFAULT now(),
  notes       text
);

-- ---------- one row per golden record ----------
CREATE TABLE golden_record (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  dataset_id          uuid NOT NULL REFERENCES eval_dataset(id),
  external_ref        text,               -- source conversation_id/message_id for traceability
  unit                eval_unit NOT NULL,
  input               jsonb NOT NULL,     -- query text and/or chat history payload
  expected_context    jsonb,              -- array of chunks.id values that SHOULD be retrieved
  expected_output      jsonb,              -- reference answer / field values / decision
  must_include        jsonb,              -- atomic facts that must appear
  must_not_include    jsonb,              -- hallucination traps / forbidden claims
  expects_refusal     boolean NOT NULL DEFAULT false,
  failure_mode        text,               -- stratum label from Phase 2 taxonomy
  difficulty          text,               -- 'easy' | 'medium' | 'hard'
  split               eval_split NOT NULL DEFAULT 'dev',
  verified            boolean NOT NULL DEFAULT false,
  verified_by         text,
  verified_at         timestamptz,
  label_rationale     text,               -- why this label, for future disputes
  created_at          timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_golden_record_dataset  ON golden_record(dataset_id);
CREATE INDEX idx_golden_record_unit     ON golden_record(unit);
CREATE INDEX idx_golden_record_verified ON golden_record(verified);
CREATE INDEX idx_golden_record_split    ON golden_record(split);

-- ---------- one row per harness execution ----------
CREATE TABLE eval_run (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  dataset_id  uuid NOT NULL REFERENCES eval_dataset(id),
  git_sha     text NOT NULL,
  config      jsonb NOT NULL,   -- rerank_threshold, vector_backend, gemini_model, temperature, prompt_hash, k
  started_at  timestamptz NOT NULL DEFAULT now(),
  tag         text
);

CREATE INDEX idx_eval_run_dataset ON eval_run(dataset_id);

-- ---------- one row per record per run ----------
CREATE TABLE eval_result (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id            uuid NOT NULL REFERENCES eval_run(id) ON DELETE CASCADE,
  record_id         uuid NOT NULL REFERENCES golden_record(id),
  actual_output     jsonb,
  retrieved_context jsonb,
  scores            jsonb,   -- {"recall_at_k": 1.0, "field_match": 0.8, ...}
  passed            boolean,
  latency_ms        integer,
  cost_usd          numeric,
  error             text,
  created_at        timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_eval_result_run    ON eval_result(run_id);
CREATE INDEX idx_eval_result_record ON eval_result(record_id);

-- ============================================================
-- Rules (enforced by the harness, not the DB):
--   - expected_context stores chunk-level ids (chunks.id), never just paper_id.
--   - records with verified = false are excluded from all scoring.
--   - any change to a verified label requires a new eval_dataset.version row,
--     never an in-place UPDATE of golden_record for a verified row.
-- ============================================================
