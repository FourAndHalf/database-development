# Learned Behaviors

This document tracks learned behaviors, successful patterns, and common pitfalls discovered while developing and interacting with the Database Research RAG system. AI coding agents should use this file to avoid repeating past mistakes and to leverage proven methodologies.

## Code Patterns & Architecture
- **Prefer Composition over Inheritance:** In `/services/ingestion`, favor compositional pipelines. For instance, `pdf_parser.py` should be decoupled from `chunker.py` and `embedder.py` to allow easy testing and swapping of implementations.
- **Asynchronous Operations:** Since vector store operations (OpenSearch/Pinecone) and LLM API calls are I/O bound, always use `asyncio` and `aiohttp`/`httpx` in the `/services/retrieval` and `/services/llm` modules to maintain throughput.
- **Error Handling:** When parsing legacy or heavily formatted academic PDFs, the PyMuPDF or pdfplumber libraries often fail silently on multi-column layouts. We've learned to implement a fallback mechanism: if text extraction yields less than 100 words per page, trigger an OCR fallback (e.g., Tesseract).

## Deployment & AWS Integrations
- **Lambda Cold Starts:** When deploying the retrieval engine to AWS Lambda, loading large transformer models for the Cross-Encoder (reranker) causes massive cold starts. We mitigate this by keeping the reranker model on a dedicated SageMaker endpoint or ECS service rather than Lambda, while Lambda only handles the orchestration.
- **OpenSearch Provisioning:** Keyword search (BM25) and k-NN vector search put different loads on OpenSearch. We learned to isolate vector search workloads to specific data nodes optimized for memory, while keyword search uses compute-optimized nodes.

## RAG Specific Learnings
- **Chunk Size Sensitivity:** Too large chunks (>1000 tokens) dilute the semantic meaning of highly dense mathematical proofs in Paxos/Raft papers. Too small chunks (<200 tokens) lose the surrounding context of algorithm steps. We found that 512 tokens with a 50-token overlap is the optimal baseline.
- **Citation Hallucinations:** Even with strict prompts, LLMs sometimes invent citation page numbers or slightly misquote. To prevent this, the `response_generator.py` MUST cross-validate the generated quote string directly against the retrieved chunk using string matching or a secondary fast validation prompt.