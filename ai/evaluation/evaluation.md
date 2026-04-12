# System Evaluation Strategy

This document outlines the holistic strategy for evaluating the Database Research RAG system. We move beyond simple unit tests to evaluate the end-to-end semantic performance of the pipeline.

## Evaluation Philosophy
"You cannot improve what you cannot measure." For a RAG system, traditional software tests are insufficient because the output is non-deterministic. We must evaluate probabilistically and statistically.

## 1. Component-Level Evaluation

### A. Parser & Chunker Evaluation
- **Metric:** Token overlap and boundary preservation.
- **Method:** Take 5 highly complex papers (e.g., Paxos, Spanner). Manually identify 10 key paragraphs. Run the chunker and assert that those paragraphs are preserved entirely within single chunks (or cleanly overlapped), rather than being split mid-sentence.

### B. Retrieval Evaluation (Offline)
- **Metric:** NDCG@5 (Normalized Discounted Cumulative Gain), Recall@5.
- **Method:** We maintain a golden dataset of 100 Query-Chunk pairs. Whenever we change the embedding model, BM25 weights, or Reranker, we run the dataset through the retrieval engine without calling the LLM.

## 2. End-to-End Evaluation (RAGAS)
We utilize the RAGAS framework for end-to-end evaluation using LLM-as-a-judge techniques.
- **Dataset:** A curated list of 50 diverse queries (`test_queries.md`).
- **Execution:** A script runs the queries through the full live pipeline, collects the answers and retrieved contexts, and passes them to the evaluation LLM (e.g., GPT-4) to score Faithfulness and Answer Relevance.

## 3. Human-in-the-Loop (HitL) Evaluation
LLM evaluators are fast but imperfect. Once a month, or before a major release:
1. **Blind Testing:** Domain experts (Database Engineers) review a random sample of 20 generated answers.
2. **Scoring:** They rate the answers on a scale of 1-5 for Technical Accuracy, Completeness, and Clarity.
3. **Feedback Loop:** Errors found during HitL are added to `failure_modes.md` and new test cases are added to `expected_answers.md`.

## 4. A/B Testing Strategy (Future)
When the UI is deployed, we will log implicit user feedback:
- Copying the answer to clipboard (Positive signal)
- Asking an immediate clarifying question (Potential negative signal/incomplete answer)
- Thumbs up/down buttons on the UI.