# System Constraints

This document outlines the hard constraints and limits of the RAG platform. AI agents must operate within these bounds when suggesting architectural changes.

## 1. Cloud & Cost Constraints
- **AWS Infrastructure Limit:** We are bound to AWS. Do not propose migrations to GCP/Azure services unless absolutely necessary.
- **OpenSearch Serverless:** We use the serverless offering. It has limitations on custom plugins. Do not suggest using OpenSearch plugins that require managing physical nodes.
- **Embedding Cost:** We process large volumes of text. We currently use local SentenceTransformer models (`all-MiniLM-L6-v2`) on AWS ECS to save costs instead of calling OpenAI's embedding API for every chunk during ingestion. Changing this requires a cost-benefit analysis.

## 2. LLM Latency Limits
- **Time-to-First-Token (TTFT):** Must be under 2 seconds. This means the Retrieval pipeline (Query -> OpenSearch -> Reranker) must execute in `< 1000ms`.
- **Context Window:** While modern LLMs have 128k+ windows, we artificially constrain the prompt to the top 10 reranked chunks (~5000 tokens) to minimize latency and prevent the "Lost in the Middle" phenomenon where the LLM forgets context.

## 3. Scope Constraints
- **Domain Strictness:** The system is strictly for distributed systems and database research. It is *not* a general programming assistant. It should refuse to write generic Python scripts or answer front-end framework questions unless they are explicitly related to a database driver mentioned in a paper.

## 4. Compliance & Legal
- **Copyright:** We only index publicly available academic papers, preprints (arXiv), or vendor whitepapers. Do not scrape paywalled databases (e.g., IEEE Xplore, ACM Digital Library) without verifying open-access status.