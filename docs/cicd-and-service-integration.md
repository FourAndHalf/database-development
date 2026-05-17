# CI/CD and Service Integration Blueprint

This project currently has ingestion/retrieval components but needs operational services around them for smooth production behavior.

## Services to add

1. OpenSearch (primary search and vector index)
- Dense vector fields for embeddings.
- BM25 fields for keyword scoring.
- Alias strategy for zero-downtime reindexing (`db-research-rag-active` -> versioned index).

2. Redis (query/result caching)
- Cache retrieval and rerank responses for repeated prompts.
- Store index metadata snapshot and hot-query keys.

3. Object storage (S3)
- Raw PDFs and parsed/chunked artifacts.
- Versioned data snapshots for reproducibility.

4. Orchestration runtime
- ECS/EKS/Lambda depending on latency and budget targets.
- Separate ingestion jobs from online query service.

5. Observability stack
- CloudWatch logs/metrics for API and ingestion jobs.
- Alerting on index health, queue lag, and cache hit ratio.

## CI pipeline

GitHub Actions `ci.yml` now enforces:
- Lint (`ruff`)
- Type checks (`mypy`)
- Security scan (`bandit`)
- Dependency audit (`pip-audit`)
- Tests (`pytest`)
- Build artifact upload

## CD pipeline

GitHub Actions `cd.yml` provides:
- Branch-based environment routing (`develop` -> `dev`, `main` -> `prod`)
- AWS OIDC-based auth (`AWS_DEPLOY_ROLE_ARN` secret)
- Deploy step placeholder
- Post-deploy index/cache hook placeholder

## Required GitHub secrets

- `AWS_DEPLOY_ROLE_ARN`
- `OPENSEARCH_URL`
- `OPENSEARCH_INDEX`
- `REDIS_URL`

## Search index integration contract

Define service-level methods in retrieval layer:
- `create_or_update_index(index_name, mapping)`
- `bulk_upsert_chunks(index_name, docs)`
- `switch_alias(alias_name, target_index)`
- `hybrid_search(query, embedding, top_k)`

Recommended mapping pattern:
- `content` as text (BM25)
- `content_vector` as `knn_vector` (dim from `EMBEDDING_DIMENSION`)
- metadata fields (`paper`, `section`, `year`, `tags`)

## Cache integration contract

Define cache keys in retrieval layer:
- `rag:query:{hash(query)}:k={k}` for top-k retrieval
- `rag:answer:{hash(full_prompt)}` for grounded final answers

Suggested policy:
- TTL default 15 minutes (`CACHE_TTL_SECONDS=900`)
- Cache only successful, grounded responses
- Invalidate on index alias switch

## Local development

Start local dependencies:

```bash
docker compose -f infra/docker/docker-compose.rag.yml up -d
```

Use `configs/service.env.example` to create your runtime env file and wire these values into `services/retrieval/vector_store.py` and `services/retrieval/hybrid_search.py`.
