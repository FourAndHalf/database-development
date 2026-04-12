# Reranking Strategy

This document details why and how we use a Cross-Encoder for reranking the initial search results.

## The Need for Reranking
1. **Vector Search (Bi-Encoder) is Fast but Shallow:** Dense embeddings compress a 512-token chunk into a single point in space. It captures semantic similarity but misses intricate relationships (e.g., "A causes B" vs "B causes A").
2. **BM25 is Exact but Brittle:** Keyword search finds exact matches but misses synonyms (e.g., missing "consistent hashing" when the query asks for "chord ring").

## The Two-Stage Pipeline
1. **Stage 1 (Retrieve):** We use OpenSearch to perform a Hybrid Search (BM25 + k-NN Vector). This is fast. We retrieve a broad set of `Top-K = 50` chunks.
2. **Stage 2 (Rerank):** We pass the user's query and the 50 retrieved chunks to a Cross-Encoder model.

## Cross-Encoder Architecture
Unlike Bi-Encoders which embed the query and document separately, a Cross-Encoder concatenates them: `[CLS] User Query [SEP] Document Chunk [SEP]` and passes the entire string through the Transformer layers.
- **Advantage:** Self-attention mechanisms can evaluate the relationship between every word in the query and every word in the document simultaneously.
- **Disadvantage:** Extremely computationally expensive. Cannot be used for searching the whole database.

## Model Selection
- We currently utilize `cross-encoder/ms-marco-MiniLM-L-6-v2` hosted on a dedicated AWS SageMaker endpoint.
- **Thresholding:** We only pass the Top-K (e.g., 5 to 7) chunks with a Cross-Encoder score above a certain threshold (e.g., > 0.5) to the final LLM prompt. If no chunks pass the threshold, the system should trigger a "I don't know" response rather than hallucinating.