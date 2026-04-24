# Experiments Summary

## Exp 001: Docling Preprocessing
- **Objective:** Extract structural data (sections, tables) from raw PDF files.
- **Methodology:** Used `docling` library's `DocumentConverter` to process `dynamo_amazons_highly_available_key_value_store.pdf` and `bigtable_a_distributed_storage_system_for_structured_data.pdf`. Output was converted to JSON.
- **Findings & Performance:** The pipeline successfully utilized `rapidocr` and downloaded missing models dynamically. Parsing time was ~24s for the Dynamo paper and ~12s for the Bigtable paper. 
- **Architectural Insights:**
  - Standardized JSON outputs from Docling capture structural layout effectively.
  - The extraction script strictly adheres to the idempotency rule (overwrites output deterministically) and error handling guidelines (logs exceptions with stack traces instead of silently passing).
  - High-fidelity parsing with OCR is compute-heavy. Deployments should consider dedicated worker nodes for the ingestion service.

## Exp 002: OpenAI Embeddings
- **Objective:** Chunk the parsed JSONs and generate vector embeddings, evaluating batch processing efficiency.
- **Methodology:** Reconstructed `DoclingDocument` models from the parsed JSON and applied `HierarchicalChunker`. Generated 290 chunks. Used a simulated `text-embedding-3-small` API to evaluate batch throughput.
- **Findings & Performance:** 
  - Token counting via `tiktoken` (using `cl100k_base` encoding) indicated roughly 38.7k tokens across the 290 chunks.
  - **Batch Efficiency Evaluation:**
    - Batch Size 10: ~8,190 tokens/sec
    - Batch Size 50: ~16,693 tokens/sec
    - Batch Size 100: ~19,070 tokens/sec
- **Architectural Insights:**
  - Batching requests to the LLM/Embedding API yields a non-linear but significant performance boost due to reduced network overhead per token.
  - The ingestion pipeline architecture *must* implement batch processing, clustering chunks before pushing to the embedding service.

## Exp 003: OpenSearch Hybrid Search
- **Objective:** Simulate a hybrid search using BM25 and KNN scoring combinations.
- **Methodology:** Used `rank_bm25` for lexical search and `numpy` for dot-product-based cosine similarity (KNN) over normalized vectors.
- **Findings & Performance:** 
  - Both components executed sub-second on the small test dataset. 
  - An `alpha` weight of 0.5 successfully retrieved expected context. For example, the query "How does Dynamo handle vector clocks" returned chunk 67 of the Dynamo document with a 1.0 BM25 score, ensuring deterministic retrieval of exact terminology.
- **Architectural Insights:**
  - Hybrid search mitigates the 'black-box' nature of dense embeddings by keeping exact keyword match behavior (BM25) intact.
  - Normalization strategy (Min-Max) is essential before combining scores, as BM25 scores are unbounded while Cosine Similarity (with normalized vectors) is bounded to [-1, 1].
  - The simplified script follows type-hinting governance rules and establishes the logical baseline for the eventual `services/retrieval/hybrid_search.py` module.
