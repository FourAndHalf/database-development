# Decisions → Metrics (draft — needs your sign-off)

Per the guide's Phase 1 rule: every metric must answer "if this number moves by X, we will do Y." Anything without an action attached gets cut. This is a **draft** — you set the asymmetric cost ratio and confirm/cut rows below.

## Candidate decisions this eval should inform

| Decision (this repo, concretely) | Minimum metric | If it moves... |
|---|---|---|
| Change `RERANK_THRESHOLD` (currently 0.5) | Recall@5 (component), refusal-rate on out-of-scope records (task) | Recall drops beyond gate → revert threshold change; refusal-rate drops on genuinely out-of-scope queries → threshold too permissive |
| Swap `GEMINI_MODEL` version, or change Groq fallback model | Faithfulness / `must_not_include` violation rate (task) | Violation rate increases beyond noise floor → block the model swap |
| Change chunk size/overlap in `chunker.py` | Recall@5, Context Precision (component) | Recall drops → revert chunking change |
| Switch `VECTOR_BACKEND` (chroma ↔ pgvector) | Recall@5, retrieved-chunk-set parity between backends (component) | Divergence beyond noise floor → investigate backend-specific bug before switching in prod |
| Change system prompt / output-format contract | `schema_valid` (does `<main>`/`<tab>` extraction succeed), `must_include` coverage (task) | Parse-failure rate rises → revert prompt change |
| Add/change the `@web-search` escape hatch logic | Refusal-rate on in-scope-but-unindexed queries (task) | — |

## Open — needs your call

- **Asymmetric cost ratio**: this system explicitly favors refusal over hallucination (`expected_answers.md`'s old draft said "never fallback to pretrained weights" — that instinct is right, but I'm not setting the actual ratio). Rough framing: a confidently wrong technical claim (hallucinated citation, fabricated benchmark number) is a trust-destroying failure; an unnecessary refusal on an answerable question is an annoyance. **You set the multiplier** used to weight the composite score in Phase 11 — this draft assumes false-positive-confident-wrong costs more, but by how much is your call.
- Cut anything above that doesn't map to an action you'd actually take.

## Phase 3 — Unit of evaluation

Two separate units, never averaged together:

- **Component level** — one retrieval call: does the reranked top-k chunk set match `expected_context`? Cheap, deterministic, high volume. Scored with `recall@k`/`precision@k`/`nDCG@k` against chunk IDs.
- **Task level** — one full turn: does the final `<main>`/`<tab>` answer satisfy `must_include`/`must_not_include`/`expects_refusal` against the user's actual question? Fewer records, higher stakes — this is where the asymmetric cost ratio applies. Scored with deterministic checks (Phase 7) plus the LLM judge (Phase 8) for the residue (reasoning quality, tone, appropriate hedging).

Each `golden_record` row is tagged `unit = 'component' | 'task'` (see `eval/dataset/migrations/001_eval_schema.sql`) and reported separately — never blended into one number.
