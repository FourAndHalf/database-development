# Batch 01 — real-traffic sample

**8 runs, not the 30-50 the guide recommends.** Source: `messages` table (Go-gateway chat memory), filtered to `role='assistant' AND sources IS NOT NULL` — the only real assistant replies in the live DB with retrieval evidence attached (`requests`/`request_retrievals`, the canonical eval-shaped tables, currently have 0 rows — not being written by the app).

Each `run-NN.md` is one real query → retrieved chunks → final answer, pulled straight from `nexus_db`, with a blank `note:` field for you to fill in per the guide's Phase 2 process (plain-language, no categories yet).

## Already-found issue: pairing ambiguity

`run-02.md` and `run-07.md` are marked **AMBIGUOUS**: in both cases, two user messages were sent before either got answered (a request race), so which query the logged answer is actually responding to isn't mechanically certain from `created_at` order alone. `run-07` is a good example — the query queue was `["B-Trees vs LSM comparison", "iran war news @web-search"]`, and the answer that landed is clearly the B-Trees one (content-inspectable), meaning the *actual* response to the Iran-war query is a different, separate assistant message (`6d20deda...`, a refusal — "I couldn't find anything relevant") that has no `sources` and so isn't in this batch at all.

This points at a real schema gap worth carrying into the Phase 2 taxonomy discussion: **`messages` has no request/response linkage id**, so query→answer pairing from raw chat history is ambiguous under concurrent sends. Worth deciding whether to (a) treat this as a one-off artifact of manual testing, or (b) add a `request_id`/`in_reply_to` column so eval sampling (and the product itself) can pair reliably going forward.

## Before writing notes

Recommend driving ~25-40 more varied queries through the live UI first (mix of fact-retrieval, multi-doc comparison, out-of-domain, and edge-case queries — see the old `ai/evaluation/test_queries.md` categories for inspiration, though that file's tech claims are stale) so Phase 2's taxonomy isn't built from 8 examples that happen to be mostly "Summarize X" queries. Not required to proceed — just flagging that 8 is thin for discovering a 5-8 mode taxonomy.
