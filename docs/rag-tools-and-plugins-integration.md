# RAG Development Tools & Plugins Integration Guide

This guide lists the core tools/plugins for smooth development of this RAG project and gives integration steps for each one.

## Tool Names (Top Index)

| Stage | Tool / Plugin | Primary Purpose |
|---|---|---|
| Document preprocessing | **Docling** | Parse PDFs into structured, chunk-ready text/metadata |
| Embeddings | **OpenAI Embeddings** (`text-embedding-3-small/large`) | Generate dense vectors for semantic retrieval |
| Search + Vector DB | **Amazon OpenSearch** (BM25 + KNN) | Hybrid retrieval (keyword + vector) |
| Reranking | **Cross-Encoder Reranker** (SageMaker endpoint or local model) | Improve precision of top retrieved chunks |
| RAG orchestration | **LangChain** or **LlamaIndex** | Manage retrieval, prompt assembly, and chain composition |
| LLM generation | **OpenAI / Anthropic SDK** | Grounded answer generation from retrieved context |
| Evaluation | **RAGAS** | Faithfulness, relevance, and retrieval quality checks |
| Experiment tracking | **MLflow** | Track runs for chunking/embedding/reranking changes |
| Observability | **Langfuse** + **OpenTelemetry** | Prompt/trace analytics and latency/error monitoring |
| Secrets/config | **AWS Secrets Manager** + **SSM Parameter Store** | Centralized secret/config management |
| Dev quality | **Ruff + Black + MyPy + pytest + pre-commit** | Fast local quality gate for reliable iteration |
| CI/CD + IaC | **GitHub Actions + Terraform** | Automated tests/deployments and reproducible infra |

---

## 1) Docling (Document Preprocessor)

### Integration Steps
1. Add Docling to ingestion dependencies and pin a compatible version in your dependency file.
2. In `services/ingestion/pdf_parser.py`, replace basic text extraction with Docling document conversion.
3. Normalize Docling output into your project schema:
   - `paper_id`, `title`, `authors`, `year`
   - section hierarchy
   - page-level references
   - extracted tables/figures (when available)
4. Write parsed artifacts to `data/parsed/` as deterministic JSON (stable keys and ordering).
5. Pass normalized section text to `services/ingestion/chunker.py`.

### Validation
1. Run parser on at least 5 complex PDFs (multi-column + tables).
2. Confirm page references and section boundaries are preserved.
3. Verify chunker input does not contain boilerplate noise (headers/footers/page numbers).

---

## 2) OpenAI Embeddings

### Integration Steps
1. Store API key in AWS Secrets Manager (or local `.env` for development only).
2. In `services/ingestion/embedder.py`, implement batch embedding with retry and backoff.
3. Persist embedding metadata with each vector:
   - `chunk_id`, `paper_id`, `section`, `page`, `embedding_model`, `embedding_version`.
4. Add a configurable embedding model selector (`small` for cost, `large` for quality experiments).
5. Log token usage and per-batch latency.

### Validation
1. Ensure all chunks receive exactly one embedding vector.
2. Spot-check cosine-neighbor quality for 10 representative queries.
3. Compare retrieval Recall@5 between model variants.

---

## 3) Amazon OpenSearch (Hybrid Retrieval Store)

### Integration Steps
1. Create an OpenSearch index with:
   - text fields for BM25
   - vector field (`knn_vector`) for semantic search
   - metadata fields for filtering (`paper`, `year`, `topic`).
2. In `services/retrieval/vector_store.py`, implement upsert + idempotent reindexing.
3. In `services/retrieval/hybrid_search.py`, execute BM25 and vector queries in parallel.
4. Fuse rankings using Reciprocal Rank Fusion (RRF) before reranking.
5. Add structured filters for paper/date/topic constraints.

### Validation
1. Verify chunk counts match between parsed source and indexed documents.
2. Confirm top-k hybrid results include both lexical and semantic matches.
3. Track Recall@5 and NDCG@5 on golden query set.

---

## 4) Cross-Encoder Reranker

### Integration Steps
1. Choose deployment mode:
   - hosted endpoint on AWS SageMaker, or
   - local model service for development.
2. In `services/retrieval/reranker.py`, score fused candidates against the user query.
3. Rerank top 20–50 candidates and keep top 3–8 context chunks.
4. Return score + rank metadata for observability.
5. Add timeout fallback to non-reranked hybrid results.

### Validation
1. Measure precision@k before vs after reranking.
2. Check latency budget impact (p95).
3. Verify fallback path under endpoint timeout/failure.

---

## 5) LangChain / LlamaIndex (RAG Orchestration)

### Integration Steps
1. Introduce an orchestration layer for request flow:
   - query normalization
   - retrieval call
   - reranking
   - prompt assembly
   - generation.
2. Keep business logic in `services/` modules and use framework wrappers for composition only.
3. Centralize prompt templates in `ai/prompting/`.
4. Add deterministic chain settings for reproducible evaluation runs.
5. Expose trace IDs for each request.

### Validation
1. Confirm end-to-end chain is deterministic for fixed inputs and temperature.
2. Ensure exceptions surface actionable error messages.
3. Validate trace ID continuity across retrieval and generation logs.

---

## 6) OpenAI / Anthropic SDK (Generation)

### Integration Steps
1. In `services/llm/prompt_builder.py`, enforce grounded prompt format with citations.
2. In `services/llm/response_generator.py`, call selected provider via adapter pattern.
3. Implement configurable model routing and fallback model.
4. Enforce guardrails from `ai/prompting/guardrails.md`.
5. Log completion tokens, latency, and refusal/failure signals.

### Validation
1. Confirm every answer includes source citations.
2. Validate behavior for empty retrieval context (safe decline pattern).
3. Track faithfulness score changes per model version.

---

## 7) RAGAS (Evaluation Framework)

### Integration Steps
1. Build an evaluation dataset from:
   - `ai/evaluation/test_queries.md`
   - expected references in `ai/evaluation/expected_answers.md`.
2. Create an offline evaluation script that records:
   - Faithfulness
   - Answer Relevance
   - Context Precision/Recall.
3. Run evaluation after every material change in chunking, embeddings, retrieval, reranker, or prompts.
4. Publish score deltas to CI artifacts.
5. Add pass/fail quality gates for deployment.

### Validation
1. Ensure evaluation is repeatable with fixed seed/config.
2. Detect regressions with threshold-based blocking rules.
3. Store historical scores for trend analysis.

---

## 8) MLflow (Experiment Tracking)

### Integration Steps
1. Stand up MLflow tracking server (or managed equivalent on AWS).
2. Log experiment parameters:
   - chunk size/overlap
   - embedding model/version
   - retrieval and reranker params
   - prompt version.
3. Log metrics from RAGAS and latency/cost counters.
4. Attach artifact links (evaluation reports and sample outputs).
5. Define tags for environment (`dev/stage/prod`) and release candidate.

### Validation
1. Confirm every experiment run has both params and metrics.
2. Ensure comparison views clearly show winning configs.
3. Verify run IDs are referenced in release notes.

---

## 9) Langfuse + OpenTelemetry (Observability)

### Integration Steps
1. Instrument API and service boundaries with OpenTelemetry traces.
2. Send LLM/prompt traces to Langfuse with prompt and model version tags.
3. Capture critical spans:
   - retrieval latency
   - reranker latency
   - LLM latency
   - total request latency.
4. Add dashboards and alerts for p95 latency, error rate, and token-cost spikes.
5. Redact sensitive payloads before logging.

### Validation
1. Verify full trace from API call to final response exists for sampled requests.
2. Trigger an alert test and verify notification routing.
3. Confirm no secrets/PII are present in observability payloads.

---

## 10) AWS Secrets Manager + SSM Parameter Store

### Integration Steps
1. Store API keys and credentials in Secrets Manager.
2. Store non-secret runtime config in Parameter Store.
3. Attach least-privilege IAM roles to API and pipeline services.
4. Implement startup-time config loading with cache + refresh strategy.
5. Add secret rotation process for third-party provider keys.

### Validation
1. Verify services run without local plaintext secrets in production.
2. Confirm secret rotation does not break runtime calls.
3. Audit IAM policies for minimum required access.

---

## 11) Ruff + Black + MyPy + pytest + pre-commit

### Integration Steps
1. Configure formatting, linting, type checks, and tests as local pre-merge gate.
2. Add `pre-commit` hooks for fast feedback before commit.
3. Include minimal smoke tests for ingestion, retrieval, and response generation modules.
4. Enforce consistent settings across local and CI execution.
5. Document one command for local verification.

### Validation
1. Ensure hook chain blocks invalid commits.
2. Confirm type checks catch interface drift in service modules.
3. Keep test runtime fast enough for developer iteration.

---

## 12) GitHub Actions + Terraform

### Integration Steps
1. Create CI workflow stages:
   - lint/type/test
   - offline evaluation gate
   - package and deploy.
2. Manage AWS infrastructure with Terraform modules (networking, OpenSearch, compute, IAM, secrets).
3. Add environment promotion rules (`dev` -> `stage` -> `prod`) with manual approvals.
4. Use remote Terraform state and state locking.
5. Publish deployment metadata (commit SHA, model/prompt versions, evaluation run ID).

### Validation
1. Verify failed quality gates block deployment.
2. Confirm Terraform plan/apply is reproducible and auditable.
3. Validate rollback by redeploying prior known-good artifact.

---

## Recommended Rollout Order

1. `Docling` preprocessing + parsed schema stabilization  
2. OpenSearch hybrid index + embedding pipeline  
3. Reranker + orchestration chain  
4. Evaluation + experiment tracking  
5. Observability + security hardening  
6. CI/CD + Terraform-driven promotion

