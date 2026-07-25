# Building a Golden Dataset & Eval Harness — Agent Build Guide

**Audience:** a coding agent working inside an existing RAG / LLM pipeline repo, with a human operator available.

**Goal:** produce a versioned, human-verified golden dataset and a runnable eval harness that detects regressions and attributes failures to a specific pipeline stage.

---

## Prime directive

> **The agent never invents golden labels.**

Ground truth comes from a human, or from an authoritative source in the codebase (a verified DB record, a signed-off document, an existing manual QA sheet). An agent-generated label is a guess wearing a lab coat, and a golden dataset built from guesses will produce confident numbers that are wrong.

The agent **may** autonomously:
- read the repo, infer architecture, propose schemas
- write scoring code, runners, CLIs, migrations
- draft *candidate* records with labels left blank or marked `unverified`
- sample and cluster real outputs for human review

The agent **must stop and ask** before:
- marking any record `verified`
- deciding the failure taxonomy (Phase 2)
- setting metric thresholds (Phase 11)
- editing an existing verified label

Records default to `verified = false` and are excluded from scoring until a human flips them.

---

## Order of work

Build in this order. Do not jump ahead to the harness — infrastructure is the *last* thing that adds value, and building it first locks in the wrong abstractions.

```
0. Recon
1. Decisions → metrics
2. Error analysis (human-led)
3. Unit of evaluation
4. Storage schema
5. Seed set: 20 records
6. Manual grading baseline
7. Deterministic scorers
8. LLM judge + judge validation
9. Expand to ~120, stratified
10. Runner + versioning
11. Thresholds + composite score
```

---

## Phase 0 — Recon

Before writing anything, map the pipeline and report back.

**Do:**
- Identify each stage that can independently fail. Typical: ingest/parse → chunk → embed → retrieve → rerank → prompt assembly → generate → post-process/validate.
- Locate where inputs and outputs are already persisted (logs, DB tables, traces, observability tooling). Existing production traffic is the best source of golden records.
- Note the retrieval unit's stable identifier (chunk id, doc id + offset). If chunks have no stable ID across re-ingestion, **flag this immediately** — it must be fixed first, or retrieval scoring is impossible.
- Note determinism levers available: temperature, seed, fixed model versions.

**Deliverable:** `eval/NOTES-architecture.md` — stage list, failure surface per stage, where real traffic can be sampled, chunk-ID stability assessment.

**Checkpoint:** confirm the stage list with the human before proceeding.

---

## Phase 1 — Decisions → metrics

For every metric, write the sentence: *"If this number moves by X, we will do Y."* Any metric with no action attached gets cut.

**Do:**
- List the 3–6 real decisions this eval must inform (ship a prompt change; adjust a confidence/routing threshold; swap embedding model; change chunk size; enable/disable reranker).
- Map each decision to the minimum metric that settles it.
- Identify the **asymmetric failure direction** — which error costs more, a false positive or a false negative — and record the rough cost ratio. This drives weighting later.

**Deliverable:** `eval/METRICS.md` — table of decision → metric → why this metric settles it.

Resist the twenty-metric dashboard. Four metrics that change behaviour beat twenty that get ignored.

---

## Phase 2 — Error analysis (human-led, do not skip)

This is the highest-value step and the one most often skipped. The failure taxonomy must be *discovered from real outputs*, not designed in the abstract.

**Agent does:**
- Sample 30–50 real pipeline runs. Stratify crudely if possible (different input types, lengths, sources). Avoid sampling only recent traffic if that biases toward one workload.
- Render each run in a readable format: input, retrieved context, final output, any metadata. Write to `eval/error-analysis/batch-01/`.
- Provide a free-text note field per run.

**Human does:**
- Reads them. Writes a plain-language note on what went wrong, per failure. No categories yet — categories come *after* reading.

**Agent then does:**
- Cluster the human's notes into 5–8 named failure modes.
- Propose the cluster names and per-cluster counts back to the human.

**Deliverable:** `eval/FAILURE-MODES.md` — named modes, description, observed frequency, an example run ID for each, and estimated cost/severity.

**Checkpoint:** human approves the taxonomy. This list becomes the stratification plan for the dataset.

---

## Phase 3 — Unit of evaluation

Decide what a single row represents. Most pipelines need two levels, and mixing them yields a number that means nothing.

Typical split:
- **Component level** — one retrieval, one extracted field, one classification. Deterministic, cheap, high volume.
- **Task level** — the end-to-end outcome the user actually cares about. Fewer records, higher stakes, this is where asymmetric cost lives.

**Do:**
- Define both units explicitly, in writing.
- Keep them in separate tables with separate metrics. Never average across them.

**Deliverable:** a short section in `eval/METRICS.md` defining each unit and which metrics apply to it.

---

## Phase 4 — Storage schema

Store the dataset in a real database (or versioned JSONL if the project has no DB). Ad-hoc spreadsheets do not survive contact with iteration — though a spreadsheet is a fine *labeling* surface that gets imported.

Adapt to the project's stack; the shape matters more than the dialect.

```sql
-- versioned dataset container
CREATE TABLE eval_dataset (
  id            SERIAL PRIMARY KEY,
  version       TEXT NOT NULL UNIQUE,   -- 'v1', 'v2' — bump on any label change
  created_at    TIMESTAMPTZ DEFAULT now(),
  notes         TEXT
);

-- one row per golden record
CREATE TABLE golden_record (
  id                  SERIAL PRIMARY KEY,
  dataset_id          INT REFERENCES eval_dataset(id),
  external_ref        TEXT,        -- source run/doc id for traceability
  unit                TEXT NOT NULL,      -- 'component' | 'task'
  input               JSONB NOT NULL,     -- query and/or input payload
  expected_context    JSONB,              -- array of chunk/doc IDs that SHOULD be retrieved
  expected_output     JSONB,              -- reference answer, field values, or decision
  must_include        JSONB,              -- atomic facts that must appear
  must_not_include    JSONB,              -- hallucination traps / forbidden claims
  expects_refusal     BOOLEAN DEFAULT false,
  failure_mode        TEXT,               -- stratum label from Phase 2
  difficulty          TEXT,               -- 'easy' | 'medium' | 'hard'
  split               TEXT DEFAULT 'dev', -- 'dev' | 'holdout'
  verified            BOOLEAN DEFAULT false,
  verified_by         TEXT,
  verified_at         TIMESTAMPTZ,
  label_rationale     TEXT                -- why this label, for future disputes
);

-- one row per harness execution
CREATE TABLE eval_run (
  id            SERIAL PRIMARY KEY,
  dataset_id    INT REFERENCES eval_dataset(id),
  git_sha       TEXT NOT NULL,
  config        JSONB NOT NULL,   -- model, k, chunk size, temperature, prompt hash
  started_at    TIMESTAMPTZ DEFAULT now(),
  tag           TEXT
);

-- one row per record per run
CREATE TABLE eval_result (
  id                SERIAL PRIMARY KEY,
  run_id            INT REFERENCES eval_run(id),
  record_id         INT REFERENCES golden_record(id),
  actual_output     JSONB,
  retrieved_context JSONB,
  scores            JSONB,   -- {"recall_at_k": 1.0, "field_match": 0.8, ...}
  passed            BOOLEAN,
  latency_ms        INT,
  cost_usd          NUMERIC,
  error             TEXT
);
```

**Rules:**
- `expected_context` stores **chunk-level** IDs, not just document IDs. Document-level truth cannot distinguish good retrieval from a lucky hit inside a long document.
- Records with `verified = false` are excluded from all scoring.
- Any change to a verified label requires a new `eval_dataset.version` row — never mutate in place.

---

## Phase 5 — Seed set: exactly 20 records

Twenty feels uselessly small. It is not. Its job is to surface design flaws in the harness *before* anyone labels 150 records.

**Agent does:**
- Select 20 candidates drawn from real traffic, covering every Phase 2 failure mode, deliberately oversampling rare-but-expensive modes.
- Pre-fill everything mechanically derivable: the input, the source reference, the failure-mode tag.
- Leave `expected_context`, `expected_output`, `must_include` **blank**.
- Generate a labeling surface — CSV/spreadsheet export or a minimal local form — with a `label_rationale` field.

**Human does:** fills in ground truth. Writes a one-line rationale for each.

**Agent does:** imports, sets `verified = true`, reports coverage per failure mode.

**Sourcing rule:** golden inputs come from real usage — real queries, real documents, real tickets. Do **not** generate queries by asking an LLM to write questions about your own chunks. Those are trivially retrievable by the same embedding model that produced the chunks; you will score in the high 90s and learn nothing.

---

## Phase 6 — Manual grading baseline

Before writing a single scorer, establish what "correct" looks like in human hands.

**Do:**
- Run the *current, unmodified* pipeline over the 20 seed records. Persist outputs.
- Export a grading sheet: input, retrieved context, actual output, expected output, plus a human score column (pass/fail or 1–5) and a reason column.

**Human does:** grades all 20.

**Why this matters:** it yields an honest baseline number, and it becomes the labeled set used in Phase 8 to validate the LLM judge. Skip it and there is no way to know whether the judge is any good.

**Deliverable:** `eval/baseline-manual.md` — date, git SHA, config, scores, human commentary.

---

## Phase 7 — Deterministic scorers only

No LLM judging in this phase. Extract as much determinism as possible first; the judge should only handle what genuinely resists it.

**Implement:**

| Scorer | Applies to | Notes |
|---|---|---|
| `recall@k`, `precision@k` | retrieval | set comparison on chunk IDs |
| `MRR` / `nDCG@k` | retrieval | when rank order matters |
| `exact_match` / `normalized_match` | structured extraction | normalize case, whitespace, dates, currency, unicode **before** comparing |
| `must_include` coverage | generation | substring or normalized-token presence of atomic facts |
| `must_not_include` violations | generation | hallucination trap detection |
| `refusal_detected` | out-of-scope records | pattern or classifier on the refusal path |
| `citation_validity` | generation | every cited ID exists and was actually retrieved |
| `schema_valid` | structured output | parses and conforms |
| decision confusion matrix | task level | keep FP and FN as **separate** counts, never collapsed into accuracy |

**Normalization warning:** at first run, most apparent failures are formatting artifacts. Build the normalizer before concluding the pipeline is broken.

**Deliverable:** `eval/scorers/` with unit tests for the scorers themselves — a scorer with a bug silently invalidates every number downstream.

Run it. Record the baseline with date + git SHA. This is the first real artifact.

---

## Phase 8 — LLM judge, then validate the judge

Only now, and only for the residue that deterministic checks cannot cover: reasoning quality, completeness, tone, appropriate hedging.

**Rubric requirements:**
- Concrete, near-binary criteria. "Is the answer helpful?" is unusable. "Does the answer state the specific figure requested?" is usable.
- Provide the reference answer to the judge.
- Force evidence before verdict — the judge cites the span justifying its score, *then* scores.
- Fixed model version, temperature 0, pinned prompt (store its hash in `eval_run.config`).
- Score one dimension per call. Multi-dimension calls produce correlated, uninformative scores.

**Validate against the Phase 6 human grades:**
- Compute agreement (Cohen's kappa, or exact-match rate for binary).
- **Below ~80% agreement, the rubric is the problem — not the model.** Tighten criteria, add examples of each score level, re-run. Iterate on the rubric, not on the labels.
- Measure judge variance: run the judge 3× over a subset at temperature 0 and record the spread. That spread is your noise floor — any regression smaller than it is not a signal.

**Deliverable:** `eval/judge/RUBRIC.md` (versioned), plus `eval/judge/validation.md` recording agreement rate and variance.

An unvalidated judge is worse than no judge: it produces confident numbers that get acted upon.

---

## Phase 9 — Expand to ~120, stratified

Coverage beats volume. 100–150 well-stratified records outperform 1,000 sampled uniformly, because natural distributions are dominated by easy cases and the 60th trivial lookup teaches nothing.

**Allocate across:**
- every Phase 2 failure mode, weighted toward high-cost modes rather than high-frequency ones
- difficulty tiers, with hard cases deliberately over-represented
- **out-of-scope records** whose correct behaviour is refusal or escalation — 10–15% of the set. Without these you optimize purely for recall and ship a system that answers everything confidently
- adversarial/edge inputs: malformed, empty, ambiguous, contradictory, unusually long

**Splits:** hold back ~20% as `holdout`, not inspected during tuning. Report dev and holdout separately. A widening gap between them means you are overfitting to the golden set — a common and real outcome.

Label in batches of ~25 with the same human workflow as Phase 5. Re-check inter-record consistency after each batch.

---

## Phase 10 — Runner + versioning

One command, reproducible, persisted.

```
eval run --dataset v1 --tag "chunk-1024" [--split dev] [--fast] [--filter failure_mode=X]
eval compare <run_id_a> <run_id_b>
eval report <run_id>
```

**Requirements:**
- Every run persists git SHA, full config (model versions, k, chunk size, temperature, prompt hash), dataset version, timestamp.
- Per-record results stored, not just aggregates — diagnosis requires drilling into individual failures.
- `compare` outputs **per-record deltas**: newly passing, newly failing, unchanged. The newly-failing list is the actual output of an eval run; the aggregate is a summary of it.
- Report scores **per stratum**, never only in aggregate. "88% overall" is not actionable; "88% overall, 40% on multi-hop, 30% on refusal cases" is.
- Two tiers: `--fast` (deterministic scorers, ~30 records, under a minute, runs on every change) and full (with judge, nightly or pre-release).
- Deterministic seeds and pinned model versions wherever the stack allows.

Emit a plain markdown or CSV report. **Do not build a dashboard.** Build one only after the numbers have changed someone's mind at least once.

---

## Phase 11 — Thresholds and a composite score

**Do:**
- Set per-metric regression gates relative to the recorded baseline (e.g. "high-cost error rate must not exceed baseline"; "retrieval recall must not drop more than 2 points").
- Define **one** composite headline number with the Phase 1 asymmetric cost ratio baked in, so the expensive failure direction dominates. Track the headline; diagnose with the breakdown.
- Gates must exceed the judge variance measured in Phase 8. A threshold tighter than your noise floor generates false alarms and gets ignored within a week.

**Checkpoint:** the human sets the numbers. The agent proposes and explains, but does not decide what level of failure is acceptable.

---

## Anti-patterns

**Editing labels to make scores improve.** When output and label disagree, exactly one of two things is true: the label is wrong (fix it, bump the dataset version, record why in `label_rationale`) or the system is wrong. Quietly "correcting" labels toward system behaviour destroys the entire apparatus, and it is the single most common way golden datasets die.

**LLM-generated queries from your own corpus.** Trivially retrievable, inflated scores, zero signal.

**Judging what could be asserted.** Every record sent to a judge that a deterministic scorer could have handled buys noise at a premium.

**A single aggregate number.** Hides exactly the stratum that is failing.

**Chasing 100%.** Unlike a unit suite, the ceiling is set by corpus quality and task ambiguity. Track direction and regressions, not perfection.

**Infrastructure before insight.** A beautiful harness scoring a taxonomy nobody derived from real failures measures nothing.

**Never inspecting the holdout gap.** Overfitting to a golden set is silent unless explicitly checked.

---

## Definition of done

- [ ] `eval/NOTES-architecture.md`, `eval/METRICS.md`, `eval/FAILURE-MODES.md` written and human-approved
- [ ] ~120 verified records, stratified across failure modes, dev/holdout split, ≥10% refusal/out-of-scope
- [ ] Deterministic scorers implemented, unit-tested, normalization handled
- [ ] Judge rubric versioned, agreement with human grades measured and ≥ target, variance recorded
- [ ] `eval run` reproducible from a git SHA, results persisted with full config
- [ ] `eval compare` produces per-record deltas
- [ ] Baseline recorded; thresholds set by the human; fast tier under a minute
- [ ] At least one real pipeline change evaluated end-to-end through the harness

---

## Suggested layout

```
eval/
  NOTES-architecture.md
  METRICS.md
  FAILURE-MODES.md
  baseline-manual.md
  dataset/
    migrations/
    seed/                 # exported labeling sheets + import scripts
  scorers/
    retrieval.py
    extraction.py
    generation.py
    normalize.py
    tests/
  judge/
    RUBRIC.md
    validation.md
    judge.py
  runner/
    run.py
    compare.py
    report.py
  reports/                # dated, committed run outputs
  error-analysis/
```

---

## Working agreement for the agent

1. Complete phases in order. Report at each checkpoint and wait.
2. Never set `verified = true` without explicit human confirmation.
3. When a golden label and pipeline output disagree, surface it — never resolve it unilaterally.
4. Prefer deterministic scoring; justify every use of a judge.
5. Keep every artifact in version control alongside the code it evaluates.
6. If the chunk-ID stability check in Phase 0 fails, stop and raise it before anything else.
