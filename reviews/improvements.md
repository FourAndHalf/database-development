# RAG & Generation Performance Improvements

**Date:** May 2026
**Status:** Planned for Post-MVP Iteration

This document outlines the architectural and codebase optimizations required to significantly speed up the Retrieval-Augmented Generation (RAG) pipeline and the LLM inference process.

---

## 1. LLM Inference Engine Overhaul
Currently, the Python backend uses the standard Hugging Face `transformers.pipeline` with `BitsAndBytes` (4-bit quantization). This is heavily bottlenecked for production inference.

*   **Switch to vLLM:** Replace `transformers` with `vLLM`. vLLM utilizes PagedAttention to efficiently manage KV cache memory, which can increase token generation throughput by 5x–10x compared to standard pipelines.
*   **Pre-quantized Models (AWQ/GPTQ):** `BitsAndBytes` computes weights dynamically during inference, which introduces high latency. We must switch to using AWQ or GPTQ pre-quantized models (e.g., `Qwen/Qwen2.5-1.5B-Instruct-AWQ`). These models are optimized for faster VRAM execution without the overhead of on-the-fly quantization.

## 2. Streaming Responses (Perceived Latency)
The API currently waits for the entire generation (often up to 2000 tokens of complex HTML and SVG data) to complete before returning a JSON response. This results in a poor user experience (long TTFT - Time To First Token).

*   **Server-Sent Events (SSE):** Modify the FastAPI endpoint (`/api/query`) to return a `StreamingResponse`. 
*   **UI Stream Parsing:** Because our prompt forces a strict XML-like structure (`<main>`, `<tab>`), the Angular frontend will require a stream parser to incrementally render the HTML and SVGs as the chunks arrive over the network.

## 3. Prompt & Output Optimization
The current system prompt mathematically guarantees high latency by demanding exhaustive answers, HTML tables, and raw SVG generation for every query.

*   **Dynamic Prompting:** Remove the strict "MUST include SVG/Table" constraints from the baseline prompt. Instead, append these instructions dynamically only if the user query explicitly asks for an "architecture diagram" or "comparison".
*   **Parallel Sub-Agent Generation:** If the complex multi-tab structure (History, Internals, Trade-offs) is mandatory, split the task. Use `asyncio.gather` to trigger three smaller, faster LLM calls simultaneously, each responsible for a single tab, rather than forcing one LLM to generate everything sequentially.

## 4. Retrieval & Embedding Optimizations
While ChromaDB is efficient, the ingestion and embedding phases can be tightened.

*   **Semantic Caching:** Implement a caching layer (e.g., Redis or GPTCache). When a query is received, embed it and check the cache for a high-similarity match (>95%). If matched, return the cached HTML response instantly, bypassing the LLM entirely.
*   **ONNX Runtime for Embeddings:** The `Embedder` class currently relies on standard PyTorch `SentenceTransformer`. Exporting the `BAAI/bge-small-en-v1.5` model to ONNX format and executing it via `onnxruntime` will reduce embedding latency by 30-50%, particularly if running on CPU architectures (like AWS Fargate).

## 5. Parallelizing I/O Bound Tasks
*   **Asynchronous Web Search:** In `main.py`, the DuckDuckGo web search (`@web-search`) is fully synchronous and halts the vector retrieval process. This needs to be wrapped in an `async` function and executed concurrently with the ChromaDB query using `asyncio.gather()`.