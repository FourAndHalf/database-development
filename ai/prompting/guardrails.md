# LLM Guardrails & Safety

This document defines the protective measures implemented in the `services/llm/response_generator.py` to prevent hallucination, data leakage, and out-of-bounds responses.

## 1. Input Guardrails (Pre-LLM)
- **Topic Filtering:** A fast classifier (or regex ruleset) checks the user query. If it contains words related to generating arbitrary code, writing essays, or topics outside of computer science, it is rejected before retrieval.
- **Prompt Injection Defense:** Queries containing phrases like "ignore previous instructions", "system prompt", or "you are now a..." are automatically flagged and rejected.

## 2. Output Guardrails (Post-LLM)
Before the response is returned to the user via the API, it must pass these checks:

### A. Citation Verification (Anti-Hallucination)
- **Regex Extraction:** Extract all strings matching `\[.*, \d{4}, p\. \d+\]`.
- **Validation:** For each extracted citation, verify that the Title and Page Number exist in the metadata of the `Top-K` chunks that were provided in the prompt.
- **Action:** If a citation does not match, the response is flagged. The system either strips the citation, returns a generic "I'm sorry, I hallucinated that reference" error, or triggers a fast LLM rewrite.

### B. "I Don't Know" Enforcement
- If the Reranker returns 0 chunks above the confidence threshold (e.g., > 0.5), the system bypasses the generation LLM entirely and immediately returns the standard fallback message: "I cannot answer this question based on the provided research papers." This saves API costs and guarantees no hallucinations.

## 3. Rate Limiting
- The API Gateway limits requests to 10 per minute per IP to prevent exhaustion of the LLM API budget.