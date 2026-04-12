# Query Rewriting Prompt

This document describes the prompt used in the `Query Analyzer` (part of the Retrieval Engine) to expand and refine the user's raw input before hitting the database.

## Objective
Users often write sloppy, vague, or acronym-heavy queries. The goal of this prompt is to translate the raw query into an optimized search payload containing synonyms and expanded acronyms.

## Current `query_prompt` Template

```markdown
You are a search query optimizer for a database research RAG system.
Your task is to take the user's raw query and expand it to improve search retrieval (BM25 and Vector Search).

Follow these rules:
1. Expand known acronyms (e.g., "LSM" -> "Log-Structured Merge Tree", "SMR" -> "State Machine Replication").
2. Identify core entities (systems, theorems, algorithms).
3. Provide 3-5 synonymous technical terms that might appear in an academic paper describing the user's query.

User's Raw Query: {user_query}

Provide your output in strictly valid JSON format:
{{
  "expanded_query": "The user's query with acronyms expanded",
  "keywords": ["keyword1", "keyword2", "keyword3", "keyword4"]
}}
```

## Integration
The output JSON from this LLM call is parsed by `services/retrieval/hybrid_search.py`. The `expanded_query` is fed into the Vector Search, and the `keywords` array is appended to the BM25 text query string.