# Docker Infrastructure Review: OpenSearch Stack

## Scope
Review target: `infra/docker/docker-compose.rag.yml`

This review focuses on architecture quality for long-term maintainability, reliability, security, and operability.

## Findings (ordered by severity)

### 1) High: Security disabled on both OpenSearch and Dashboards
- `DISABLE_SECURITY_PLUGIN=true` and `DISABLE_SECURITY_DASHBOARDS_PLUGIN=true` are set.
- This removes built-in authentication and TLS protections.

Impact:
- Acceptable only for isolated local development.
- Unsafe if this configuration is reused in shared, staging, or production-like environments.

Decision guidance:
- Keep a local profile that is explicitly non-production.
- Introduce a production-like profile with security enabled, credentials managed via secret store, and TLS termination.

---

### 2) Medium: No resource governance and memory safety controls
- OpenSearch heap is pinned (`-Xms1g -Xmx1g`) but no explicit container resource limits are documented/enforced in the compose strategy.
- Redis is configured for persistence but no memory cap or eviction policy is defined in the architecture.

Impact:
- Under host memory pressure, OpenSearch and Redis can become unstable.
- Cache behavior can become unpredictable without explicit eviction policy.

Decision guidance:
- Define resource envelopes per environment (dev/stage/prod-like).
- Define Redis max memory + eviction policy consistent with cache SLA.
- Document expected host sizing and failure behavior.

---

### 3) Medium: Health check verifies process response, not workload readiness
- OpenSearch health check checks for a `status` field in cluster health output.
- This does not guarantee indexing/search readiness for application traffic.

Impact:
- Services may pass health checks while still not ready for real query/index operations.
- Can cause flaky startup sequencing and false positives in CI/local integration.

Decision guidance:
- Define readiness as: minimum cluster health target + index template availability + smoke query success.
- Keep liveness and readiness as separate concerns.

---

### 4) Medium: No environment segmentation strategy in docker architecture
- Current compose is a single unified configuration without explicit profile policy for local vs production-like behavior.

Impact:
- Increased risk of config drift and accidental use of insecure defaults outside local machines.

Decision guidance:
- Use explicit environment profiles with clear naming and policy boundaries:
  - `local-dev` (fast startup, permissive)
  - `preprod-like` (auth, stricter checks, restricted ports)
- Document “promotion rules” between profiles.

---

### 5) Low: Version pinning is good, immutable pinning is missing
- Images are pinned by version tags.
- No digest pinning policy is documented.

Impact:
- Repeatability and supply-chain consistency can vary when tags are updated upstream.

Decision guidance:
- For high-confidence builds, define digest pinning policy for preprod/prod-like environments.

---

## Architectural Insights

1. Treat this compose stack as an integration harness, not a production deployment artifact.
2. Separate online query path dependencies from ingestion-heavy path to avoid operational coupling.
3. Define explicit index lifecycle governance:
- versioned indexes,
- alias-based switchovers,
- rollback-compatible schema changes.
4. Define cache governance:
- cache key standards,
- TTL policy,
- invalidation rule tied to index alias switch.
5. Add operational observability expectations at architecture level:
- SLO-aligned metrics for search latency, error rate, and cache hit ratio.

## Recommended ADRs to add

1. **ADR: Search Runtime Posture**
- local-dev vs production-like configuration boundaries.
- security/TLS/auth expectations.

2. **ADR: Index Lifecycle and Rollback**
- versioning, alias cutover, reindex policy, rollback steps.

3. **ADR: Cache Strategy**
- Redis usage scope, TTL, invalidation, and consistency tradeoffs.

4. **ADR: Readiness and Health Policy**
- service startup gates and workload readiness criteria.

5. **ADR: Resource and Capacity Baselines**
- memory/CPU envelopes and escalation path when saturation occurs.

## Intern Action Checklist (non-coding architecture tasks)

1. Classify current compose file explicitly as `local-dev only` until security profile is added.
2. Write profile policy doc for `local-dev` and `preprod-like`.
3. Define readiness contract for OpenSearch and Redis (what must be true before traffic).
4. Define Redis cache policy (max memory, eviction, TTL standards).
5. Define index governance policy (alias naming, reindex and rollback flow).
6. Draft the 5 ADRs above and circulate for technical review.

## Final Assessment
Current setup is a good development starting point. For long-term quality, the key gap is governance: environment segmentation, security posture, readiness criteria, and lifecycle policies for index/cache need to be formalized before this architecture can be considered production-ready.
