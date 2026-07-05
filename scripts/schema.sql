-- ============================================================
-- RAG Pipeline Schema (PostgreSQL)
-- Research-paper repository + user uploads + query history
-- Chunks & embeddings live in ChromaDB (external); Postgres is
-- the relational system-of-record and links back via paper_id.
-- Requires: PostgreSQL 14+
-- ============================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;    -- gen_random_uuid()

-- ---------- Enumerated types ----------
CREATE TYPE paper_source     AS ENUM ('curated', 'user_upload');
CREATE TYPE paper_visibility AS ENUM ('private', 'public', 'shared');
CREATE TYPE ingest_status    AS ENUM ('pending', 'processing', 'completed', 'failed');
CREATE TYPE request_status   AS ENUM ('pending', 'completed', 'failed');

-- ---------- updated_at helper ----------
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS trigger AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- users
--   activity counters (login/papers/requests) are kept correct
--   automatically by triggers / the record_login() helper below,
--   so application code never has to remember to update them.
-- ============================================================
CREATE TABLE users (
    id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    email                 text NOT NULL UNIQUE,
    username              text UNIQUE,               -- display name / handle
    full_name             text,
    password_hash         text NOT NULL,             -- store a hash, never the raw password
    region                text,                      -- e.g. 'IN-KL', 'US-CA', 'EMEA'

    -- activity counters
    login_count           integer NOT NULL DEFAULT 0,
    last_login_at         timestamptz,
    papers_uploaded_count integer NOT NULL DEFAULT 0,
    requests_count        integer NOT NULL DEFAULT 0,

    is_admin              boolean NOT NULL DEFAULT false, -- role gate: paper upload/delete + admin UI
    is_active             boolean NOT NULL DEFAULT true,
    created_at            timestamptz NOT NULL DEFAULT now(),
    updated_at            timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_users_region ON users(region);

CREATE TRIGGER trg_users_updated
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Call this at successful login to bump the counter + timestamp:
--   SELECT record_login('<user-uuid>');
CREATE OR REPLACE FUNCTION record_login(p_user_id uuid)
RETURNS void AS $$
BEGIN
  UPDATE users
     SET login_count   = login_count + 1,
         last_login_at = now()
   WHERE id = p_user_id;
END;
$$ LANGUAGE plpgsql;

-- ============================================================
-- papers  (both the shared repository and user uploads)
--   curated repo paper  -> source_type = 'curated',     uploaded_by IS NULL
--   user upload         -> source_type = 'user_upload', uploaded_by = <user>
--   NOTE: the paper's chunks/vectors live in ChromaDB, keyed by
--         this paper's id (store paper_id in each Chroma chunk's
--         metadata so you can filter + cite back).
-- ============================================================
CREATE TABLE papers (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    title             text NOT NULL,                 -- name of the paper
    authors           text[] NOT NULL DEFAULT '{}',
    abstract          text,
    doi               text UNIQUE,                   -- nullable; not all papers have one
    venue             text,                          -- journal / conference
    published_date    date,

    -- links
    source_url        text,                          -- external origin / where to download from
    storage_uri       text,                          -- your stored copy (served for download)

    source_type       paper_source     NOT NULL DEFAULT 'user_upload',
    uploaded_by       uuid REFERENCES users(id) ON DELETE SET NULL,
    visibility        paper_visibility NOT NULL DEFAULT 'private',

    -- original file
    original_filename text,
    mime_type         text,
    file_size_bytes   bigint,
    checksum_sha256   char(64),                      -- for dedup / change detection

    -- ingestion pipeline state
    status            ingest_status NOT NULL DEFAULT 'pending',
    ingested_at       timestamptz,                   -- set when ingestion completes; order by this
    chunk_count       integer NOT NULL DEFAULT 0,    -- how many chunks were written to Chroma
    error_message     text,

    created_at        timestamptz NOT NULL DEFAULT now(),
    updated_at        timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_papers_uploaded_by ON papers(uploaded_by);
CREATE INDEX idx_papers_source_type ON papers(source_type);
CREATE INDEX idx_papers_status      ON papers(status);
CREATE INDEX idx_papers_ingested_at ON papers(ingested_at);
CREATE INDEX idx_papers_checksum    ON papers(checksum_sha256);
CREATE INDEX idx_papers_authors_gin ON papers USING gin (authors);

CREATE TRIGGER trg_papers_updated
    BEFORE UPDATE ON papers
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Keep users.papers_uploaded_count in sync (user uploads only)
CREATE OR REPLACE FUNCTION bump_papers_count()
RETURNS trigger AS $$
BEGIN
  IF (TG_OP = 'INSERT') THEN
    IF NEW.uploaded_by IS NOT NULL THEN
      UPDATE users SET papers_uploaded_count = papers_uploaded_count + 1
       WHERE id = NEW.uploaded_by;
    END IF;
  ELSIF (TG_OP = 'DELETE') THEN
    IF OLD.uploaded_by IS NOT NULL THEN
      UPDATE users SET papers_uploaded_count = papers_uploaded_count - 1
       WHERE id = OLD.uploaded_by;
    END IF;
  END IF;
  RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_papers_count
    AFTER INSERT OR DELETE ON papers
    FOR EACH ROW EXECUTE FUNCTION bump_papers_count();

-- ============================================================
-- requests  (a saved user query + its generated answer)
-- ============================================================
CREATE TABLE requests (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    query_text   text NOT NULL,
    answer_text  text,
    status       request_status NOT NULL DEFAULT 'pending',
    model_name   text,                        -- generator model used
    params       jsonb NOT NULL DEFAULT '{}', -- top_k, filters, temperature, etc.
    web_search_used boolean NOT NULL DEFAULT false, -- true if the user turned on web search for this request
    latency_ms   integer,
    created_at   timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_requests_user_id ON requests(user_id);
CREATE INDEX idx_requests_created ON requests(created_at DESC);

-- Keep users.requests_count in sync
CREATE OR REPLACE FUNCTION bump_requests_count()
RETURNS trigger AS $$
BEGIN
  IF (TG_OP = 'INSERT') THEN
    UPDATE users SET requests_count = requests_count + 1 WHERE id = NEW.user_id;
  ELSIF (TG_OP = 'DELETE') THEN
    UPDATE users SET requests_count = requests_count - 1 WHERE id = OLD.user_id;
  END IF;
  RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_requests_count
    AFTER INSERT OR DELETE ON requests
    FOR EACH ROW EXECUTE FUNCTION bump_requests_count();

-- ============================================================
-- request_retrievals  (which Chroma chunks fed each answer — for
--   traceability / eval; pairs well with Phoenix-style tracing)
--   Chunks + vectors live in ChromaDB; we store the chunk id here
--   plus a cached snippet so display/audit needs no Chroma round-trip.
-- ============================================================
CREATE TABLE request_retrievals (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id      uuid NOT NULL REFERENCES requests(id) ON DELETE CASCADE,
    paper_id        uuid REFERENCES papers(id) ON DELETE SET NULL, -- cite back to paper; kept even if paper is later deleted
    chroma_chunk_id text NOT NULL,             -- id of the chunk in ChromaDB
    snippet         text,                      -- cached chunk text (optional, for display/audit)
    rank            integer NOT NULL,          -- 1 = top hit
    score           double precision,          -- similarity / rerank score
    created_at      timestamptz NOT NULL DEFAULT now(),
    UNIQUE (request_id, chroma_chunk_id)
);

CREATE INDEX idx_retrievals_request ON request_retrievals(request_id);
CREATE INDEX idx_retrievals_paper   ON request_retrievals(paper_id);
CREATE INDEX idx_retrievals_chunk   ON request_retrievals(chroma_chunk_id);
