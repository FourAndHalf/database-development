# Retrieval Strategy

This document outlines the core retrieval mechanics used to find the most relevant academic context for a user's query.

## 1. Query Analysis & Expansion
Before hitting the database, the user's query is pre-processed:
- **Acronym Expansion:** Converts "LSM" -> "Log-Structured Merge", "SMR" -> "State Machine Replication".
- **Concept Mapping:** Uses `ai/knowledge/concepts_map.md` logic. If a query mentions "Spanner and clock skew", it appends the synonym "TrueTime" to the BM25 query string.

## 2. Hybrid Search Implementation
We use a combined approach to maximize Recall.

### A. Semantic Search (k-NN)
- Uses the dense vector embeddings stored in OpenSearch.
- Excellent for conceptual queries like "Why is eventual consistency hard to program against?" where exact keywords might not match.
- Weight: `alpha = 0.6`

### B. Keyword Search (BM25)
- Standard TF-IDF based search on the raw text chunks.
- Critical for specific queries like "What does Paxos use phase 2a for?" where the exact term "phase 2a" is required.
- Weight: `beta = 0.4`

## 3. Score Fusion: Reciprocal Rank Fusion (RRF)
Since BM25 scores (unbounded) and Cosine Similarity scores (0 to 1) are not directly comparable, we use RRF to combine the lists.

`RRF_Score = 1 / (k + Rank_Vector) + 1 / (k + Rank_BM25)`
*(where k is a constant, typically 60)*

## 4. Metadata Filtering (Pre-filtering)
If the Query Analyzer detects specific constraints (e.g., "In the Dynamo paper..."), we apply an OpenSearch term filter on the `paper_title` metadata field *before* executing the vector/BM25 search. This prevents results from other papers from bleeding in.