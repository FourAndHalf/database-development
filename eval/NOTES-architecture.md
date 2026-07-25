# Phase 0 — Architecture Recon

Confirmed against source (2026-07-25). Cross-checked against `docs/how-it-works.html` and `docs/database-and-chat-memory.html`; both are accurate to the code as of this date.

## Pipeline stages

| Stage | What it does | Source |
|---|---|---|
| Ingest/parse | Docling parses PDF structure (headings/paragraphs/tables) | `services/ingestion/pdf_parser.py` |
| Chunk | Two-pass: `HierarchicalChunker` splits by Docling structural sections, then a semantic pass splits within sections using per-sentence bge-m3 embeddings at the bottom-15th-percentile similarity cutoff (512-token target, 64-token min, ~15% overlap ≈77 tokens, `[Paper: X] [Section: Y]` header injection) | `services/ingestion/chunker.py` |
| Embed | `BAAI/bge-m3`, 1024-dim, normalized (same model at ingestion and query time) | `services/ingestion/embedder.py`, `services/ingestion/vectorize.py` |
| Retrieve | ANN search, pgvector HNSW/cosine or Chroma (backend-switchable via `VECTOR_BACKEND`, default `chroma`), top-20 candidate pool | `services/retrieval/vector_store.py`, `services/retrieval/query.py` |
| Rerank | Cross-encoder `BAAI/bge-reranker-v2-m3`, CPU, scores 20 candidates jointly with the query | `services/retrieval/reranker.py` |
| Confidence gate | `RERANK_THRESHOLD` env, default `0.5` — sub-threshold chunks dropped | `apps/api_python/routers/query.py` |
| Prompt assembly | Grounded vs. follow-up system prompt, sliding chat-history window, `<main>`/`<tab>` output-format contract | `apps/api_python/routers/query.py` |
| Generate | Gemini 2.5 Flash primary (temp 0.15) → Groq fallback (`llama-3.1-8b-instant` / `llama-3.3-70b-versatile`, temp 0.15) on exception | `apps/api_python/routers/query.py` |
| Post-process/validate | Regex extraction of `<main>`/`<tab>` blocks, raw-text fallback if contract not followed | `apps/api_python/routers/query.py` |

Escape hatches: `@web-search` (DuckDuckGo top-2, bypasses the confidence gate); honest "not found" refusal path when nothing clears the gate.

## Storage

Single Postgres (`nexus_db`), two schemas:
- Canonical (`scripts/schema.sql`): `users`, `papers`, `chunks` (pgvector column), `requests`, `request_retrievals`.
- Go-gateway-owned (`apps/api-go/internal/store/store.go`): `conversations`, `messages` (chat memory), a second simpler `papers`/`authors`/`paper_authors`/`paper_metadata` set, `daily_metrics`, `query_latency_log`.

**Gap found:** `requests` / `request_retrievals` — the tables shaped for eval traceability — have **0 rows** in the live DB. The app isn't writing to them. Real traffic lives only in `conversations`/`messages` (5 conversations, 48 messages, 21 assistant replies as of this check). Of those, only 8 assistant replies have a populated `sources` field, and `sources` stores `{paper_id (= title string, not chunks.id), title, section, snippet, page}` — **not the actual `chunks.id`**. Recovering chunk-level ground truth from these logs requires matching `snippet` text back to `chunks.content`.

## Chunk-ID stability

**Deterministic — no stop condition triggered.** `chunker.py`: `chunk_id = f"{json_path.stem}_chunk_{chunk_index:04d}"` — filename stem + zero-padded sequential index in emission order. No UUIDs, no randomness in the chunking algorithm (fixed heading tree, fixed percentile threshold recomputed per document). Re-ingesting the same paper regenerates the same chunk_ids, contingent on Docling's parse output being stable across runs (not independently stress-tested, but no randomness source exists to break it).

## Determinism levers

- Temperature: pinned at `0.15` for both Gemini and Groq. Not zero — some sampling variance remains.
- No seed parameter passed to either provider — generation is not fully deterministic even at low temp.
- Model versions: `GEMINI_MODEL` env defaults to a pinned version string (`gemini-2.5-flash`, not a floating alias); Groq model choice is a fixed lookup table, not free text.
- `RERANK_THRESHOLD` (default 0.5) and `VECTOR_BACKEND` (default `chroma`) are the two config levers most likely to be tuned — both should be recorded in `eval_run.config` on every harness run.

## Known limitation for this dataset

Real-traffic sample size is small (8 usable examples with retrieval evidence, not the 30-50 the guide recommends for Phase 2). See `eval/error-analysis/batch-01/README.md` for how this is being handled.
