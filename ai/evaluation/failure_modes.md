# Known Failure Modes

This document catalogs common ways the RAG pipeline fails. AI agents working on the `/services` directory must actively design defenses against these specific failure modes.

## 1. The "Needle in a Haystack" Failure
**Symptom:** The answer to a specific question is buried in a single sentence of a 15-page paper, and the vector search fails to rank it in the top 5 chunks.
**Root Cause:** Dense embeddings often smooth out highly specific details in favor of the chunk's overall semantic theme.
**Mitigation:** 
- Implement Hybrid Search (BM25 + Vector). The BM25 component ensures exact keyword matches (e.g., a specific algorithm name) are heavily weighted.
- Reduce chunk sizes for highly dense theoretical papers.

## 2. Cross-Paper Contradiction
**Symptom:** The LLM gets confused when retrieved chunks from different papers use the same term to mean different things (e.g., "consistency" in CAP theorem vs. "consistency" in ACID).
**Root Cause:** Lack of temporal or contextual separation in the prompt.
**Mitigation:** The `Prompt Builder` must clearly segregate chunks by paper and explicitly instruct the LLM to identify and explain differing definitions based on the author's context.

## 3. Hallucinated Citations
**Symptom:** The LLM generates a perfectly plausible answer but appends a fake citation `[Paxos Made Simple, 2001, p. 42]` (the paper is only 14 pages long).
**Root Cause:** LLMs are completion engines; they predict the statistical likelihood of a citation format without verifying its factual basis against the context.
**Mitigation:** 
- Strict system prompt guardrails.
- Post-generation validation layer: parse the generated citations and verify they exist in the metadata of the retrieved chunks.

## 4. The "Table Extraction" Trap
**Symptom:** Queries asking for benchmark numbers return garbage data.
**Root Cause:** PDFs render tables as absolute positioning of text blocks. The `pdf_parser` flattens this, destroying the column/row relationships.
**Mitigation:** 
- Use specialized OCR/Table extraction libraries (like `Camelot` or `Tabula`) for pages identified as containing tables.
- If table extraction fails, exclude the table from the vector index rather than polluting it with garbage text.