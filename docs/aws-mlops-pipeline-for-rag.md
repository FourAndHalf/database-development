# AWS MLOps Pipeline for RAG (Architecture + Execution)

This document defines a production-ready MLOps pipeline for this RAG system on AWS, including preprocessing with **Docling**, evaluation gates, deployment, and rollback.

## 1) Target Architecture

### Core AWS Services
- **S3**: raw PDFs, parsed artifacts, chunk sets, evaluation artifacts
- **Step Functions**: orchestration across ingestion/indexing/evaluation/deploy stages
- **ECS Fargate or SageMaker Processing**: Docling preprocessing, chunking, embedding jobs
- **OpenSearch**: hybrid retrieval index (BM25 + vector)
- **SageMaker Endpoint / ECS service**: reranker inference endpoint
- **API Gateway + Lambda/ECS**: online RAG API
- **CloudWatch + X-Ray + OpenTelemetry sink**: metrics, logs, tracing
- **Secrets Manager + IAM + KMS**: secret and access control baseline
- **GitHub Actions + Terraform**: CI/CD and infrastructure lifecycle

## 2) End-to-End Pipeline Stages

### Stage A: Data Intake and Versioning
1. Ingest PDFs to versioned S3 prefix (for example: `s3://.../raw/YYYY-MM-DD/`).
2. Generate immutable dataset manifest (`manifest.json`) with file checksums.
3. Register dataset version in experiment metadata store (MLflow or equivalent).
4. Trigger Step Functions state machine for pipeline run.

**Gate:** manifest complete, checksums valid, duplicate/corrupt files flagged.

### Stage B: Docling Preprocessing
1. Launch Docling job on ECS/SageMaker Processing over new raw dataset.
2. Produce normalized JSON artifacts with section hierarchy + page anchors.
3. Store output in `s3://.../parsed/<dataset_version>/`.
4. Record parser success/failure counts and per-document diagnostics.

**Gate:** parse success rate threshold met (for example `>= 98%`) and no critical schema errors.

### Stage C: Chunking and Embedding
1. Run chunker with explicit config (`chunk_size`, `overlap`, section-aware rules).
2. Generate embeddings in batches with retry/backoff and token accounting.
3. Persist chunk manifest and embedding metadata with model/version tags.
4. Store artifacts in `s3://.../chunks/<run_id>/` and `s3://.../embeddings/<run_id>/`.

**Gate:** 1:1 mapping between expected chunks and generated embeddings.

### Stage D: OpenSearch Index Build/Refresh
1. Build/refresh OpenSearch index for both text and vector fields.
2. Upsert documents idempotently using stable `chunk_id`.
3. Run retrieval smoke tests on golden queries.
4. Keep blue/green index aliases for safe swaps.

**Gate:** Recall@5/NDCG@5 minimum thresholds and index integrity checks pass.

### Stage E: RAG Evaluation and Quality Approval
1. Execute RAGAS and project-specific evaluation suite on fixed query set.
2. Compare results to baseline for faithfulness/relevance/regression.
3. Publish evaluation report artifact and run metadata.
4. Mark release candidate as approved/rejected.

**Gate:** quality thresholds met; regressions blocked automatically.

### Stage F: Deployment and Promotion
1. Deploy API service and retrieval config to `dev`.
2. Run synthetic and canary checks.
3. Promote to `stage` then `prod` with approval gates.
4. Attach release metadata:
   - dataset version
   - Docling parser version
   - embedding model version
   - reranker version
   - prompt version.

**Gate:** canary SLOs pass before full traffic shift.

### Stage G: Monitoring, Drift, and Retraining/Reindex Triggers
1. Monitor latency, error rate, token cost, retrieval quality proxy metrics.
2. Detect drift signals:
   - lower citation coverage
   - retrieval miss increase
   - user correction rate increase.
3. Trigger partial reindex or full pipeline rerun based on drift policy.
4. Capture incidents and corrective actions in release logs.

---

## 3) CI/CD Workflow (GitHub Actions + Terraform)

1. On PR:
   - lint, type-check, tests
   - offline retrieval/evaluation smoke checks.
2. On merge to main:
   - build container artifacts
   - run Terraform plan
   - run pipeline in `dev`.
3. On release tag:
   - Terraform apply for target environment
   - execute promotion pipeline with manual approval.
4. Store provenance:
   - commit SHA
   - image digest
   - Terraform plan hash
   - evaluation run ID.

---

## 4) Security and Governance Baseline

1. Use least-privilege IAM roles for each pipeline stage.
2. Encrypt S3/OpenSearch/secrets with KMS-managed keys.
3. Keep OpenSearch and compute in private subnets where possible.
4. Enforce audit logs for access to production data and secrets.
5. Define data retention and deletion policy for intermediate artifacts.

---

## 5) Rollback Strategy

1. Maintain blue/green index aliases in OpenSearch.
2. Keep previous API container image and config bundle deployable.
3. Roll back by:
   - swapping index alias to prior version
   - redeploying previous API artifact
   - restoring previous prompt/model configuration.
4. Re-run smoke tests post-rollback and mark incident closure only after SLO recovery.

---

## 6) Production Readiness Checklist

- Dataset manifest and artifact lineage enabled
- `Docling` preprocessing version tracked
- Evaluation gates enforced in CI/CD
- Canary deployment and rollback tested
- Alerts configured for latency, errors, and cost anomalies
- IAM and secret rotation policy validated
