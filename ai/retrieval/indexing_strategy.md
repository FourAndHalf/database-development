# Indexing Strategy

This document describes how data is structured and stored within our vector database (OpenSearch) to enable fast, hybrid retrieval.

## OpenSearch Index Mapping
Our primary index (`db_papers_current`) uses a custom mapping to support both dense vector search and BM25 keyword search on the same documents.

### Document Schema
```json
{
  "chunk_id": { "type": "keyword" },
  "paper_title": { "type": "keyword" },
  "authors": { "type": "keyword" },
  "year": { "type": "integer" },
  "section_header": { "type": "text" },
  "text": { 
    "type": "text", 
    "analyzer": "standard" 
  },
  "embedding": {
    "type": "knn_vector",
    "dimension": 384,
    "method": {
      "name": "hnsw",
      "space_type": "cosinesimil",
      "engine": "nmslib"
    }
  },
  "page_number": { "type": "integer" }
}
```

## Indexing Mechanics
1. **HNSW (Hierarchical Navigable Small World):** We use the HNSW algorithm for Approximate Nearest Neighbor (ANN) search. It provides the best tradeoff between query latency and recall.
2. **Cosine Similarity:** The distance metric used for the `embedding` field is Cosine Similarity, which aligns with the training objective of most SentenceTransformer models.
3. **Bulk Upsert:** The `services/ingestion/embedder.py` script batches documents into groups of 500 and uses the OpenSearch `_bulk` API to maximize indexing throughput.

## Index Maintenance
- **Refresh Interval:** Set to `1s` during normal operation, but temporarily increased to `60s` or `-1` during massive batch ingestion jobs to improve write performance.
- **Backups:** AWS OpenSearch Serverless automatically handles underlying data durability, but we maintain the source of truth in the S3 `/data/chunks/` bucket. Re-indexing from S3 should take less than 1 hour.