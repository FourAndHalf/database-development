# Data Versioning Strategy

This document defines how we handle the lifecycle and versioning of the database papers and their resulting embeddings.

## The Versioning Problem
When we change the chunking strategy, the PDF parsing library, or the embedding model, the vector index becomes stale. We cannot have a mix of old embeddings and new embeddings in the same index, as vector distances will become meaningless.

## Index Versioning Protocol
1. **Immutability:** An OpenSearch index is treated as immutable. Once created, its underlying embedding model and chunking strategy cannot change.
2. **Naming Convention:** Indexes must be named with a version and hash of the configuration:
   `db_papers_v{MAJOR}_{CONFIG_HASH}`
   Example: `db_papers_v2_a7b8c9`
3. **Alias Switching:** The API always queries an alias (e.g., `db_papers_current`). When a re-indexing job is complete, the alias is atomically swapped to the new index.

## Code Versioning (`/services/ingestion`)
Any change to `chunker.py` or `embedder.py` that alters the semantic boundaries or the vector dimensionality MUST increment the `PIPELINE_VERSION` constant in `services/ingestion/__init__.py`.

## Data Source Versioning
- **Raw PDFs:** Stored in S3 with versioning enabled. If a paper is updated (e.g., authors release a v2 of an arXiv preprint), the old version is retained.
- **Document Metadata:** The `year` field in the metadata is critical. When answering queries about the evolution of a concept, the LLM must prioritize temporal ordering based on this field.