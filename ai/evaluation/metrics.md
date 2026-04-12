# Evaluation Metrics

To ensure the RAG system remains an authoritative source, we employ strict quantitative evaluation using the RAGAS (Retrieval Augmented Generation Assessment) framework and custom heuristics.

## Core RAG Metrics

### 1. Faithfulness (Groundedness)
- **Definition:** Measures whether all claims made in the generated answer can be inferred directly from the retrieved context.
- **Goal:** `> 0.98` (Near perfect)
- **Measurement:** Use an LLM-as-a-judge to extract claims from the answer and verify if they are entailed by the chunks.

### 2. Answer Relevance
- **Definition:** Measures how well the generated answer addresses the user's initial query, penalizing incomplete or tangential answers.
- **Goal:** `> 0.90`
- **Measurement:** Generate artificial questions based on the answer and calculate cosine similarity with the original user query.

### 3. Context Precision
- **Definition:** Measures whether all the ground-truth relevant items present in the contexts are ranked higher. Evaluates the Reranker.
- **Goal:** `> 0.85`
- **Measurement:** Requires a golden dataset of Query -> Relevant Chunk mappings.

### 4. Context Recall
- **Definition:** Measures if the retrieval engine fetched all the necessary information required to answer the question.
- **Goal:** `> 0.92` (Recall@5)
- **Measurement:** Compare the retrieved chunks against a known set of ground-truth chunks for a test query.

## System Performance Metrics

### 1. Latency (P95)
- **Retrieval:** `< 400ms` (OpenSearch query + Reranking)
- **Generation:** `< 4000ms` (Time to first token / total generation time for GPT-4)
- **Total System:** `< 5 seconds`

### 2. Infrastructure Costs
- Monitor AWS OpenSearch Serverless OCUs (OpenSearch Compute Units).
- Monitor LLM Token usage per query.

## Continuous Evaluation Pipeline
1. Every PR merging into `main` that modifies `/services/retrieval` or `/services/llm` MUST trigger an automated evaluation run against the `/ai/evaluation/test_queries.md` dataset.
2. If Faithfulness drops below 0.95, the CI pipeline fails.