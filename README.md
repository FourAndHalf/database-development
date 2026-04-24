# 🗄️ Database Research RAG (Retrieval-Augmented Generation)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![CI/CD Pipeline](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-orange)](https://github.com/features/actions)
[![Infrastructure: AWS](https://img.shields.io/badge/Infra-AWS-232F3E.svg?logo=amazon-aws&logoColor=white)](https://aws.amazon.com/)

An authoritative RAG system designed to synthesize decades of database research. This project parses foundational papers (e.g., DynamoDB, Spanner, Cassandra) and provides high-fidelity, grounded answers to complex questions about distributed systems, consistency models, and storage engine architectures.

## 🚀 Overview

This system serves as a "living encyclopedia" for database engineering. By leveraging a Retrieval-Augmented Generation (RAG) architecture, it bridges the gap between raw academic research and actionable engineering insights.

### Key Capabilities
- **Foundational Knowledge:** Rooted in "Base Truth" papers from Google, Amazon, Facebook, and academia.
- **Deep Semantic Search:** Moves beyond keyword matching to understand concepts like *quorum intersections*, *linearizability*, and *LSM-tree compaction*.
- **Grounded Generation:** Every response is backed by citations from the source PDFs, eliminating LLM hallucinations.

---

## 🏛️ Architectural Design

The project follows a modular pipeline architecture designed for scalability and high precision.

### 1. Ingestion & Processing (`/services/ingestion`)
- **Document Preprocessing (Docling):** High-fidelity extraction of text, layout, tables, and citations from academic PDFs.
- **Intelligent Chunking:** Context-aware splitting of documents to preserve semantic boundaries (e.g., keeping a Paxos algorithm description intact).
- **Embedding:** Multi-stage embedding using state-of-the-art models to map database concepts into vector space.

### 2. Retrieval Engine (`/services/retrieval`)
- **Hybrid Search:** Combines dense vector retrieval (semantic) with sparse keyword search (BM25) for precise technical terminology.
- **Reranking:** Employs a cross-encoder reranker to ensure the most relevant 3-5 segments are provided to the LLM.
- **Vector Store:** Scalable storage using high-performance vector databases (OpenSearch/Pinecone) hosted on AWS.

### 3. LLM Orchestration (`/services/llm`)
- **Prompt Engineering:** Specialized system prompts that enforce "citation-first" answering.
- **Source Grounding:** Validation layer to ensure every claim corresponds to a retrieved chunk.

---

## 📚 Knowledge Base (The "Base Truth")

The system is currently indexed with over 50 foundational papers, including:

| Category | Key Papers |
| :--- | :--- |
| **Distributed Consensus** | Paxos Made Simple, Raft, Viewstamped Replication, EPaxos |
| **NoSQL & Key-Value** | Dynamo (Amazon), Bigtable (Google), Cassandra (Facebook), RocksDB |
| **Distributed SQL** | Spanner (Google), CockroachDB, F1, Aurora |
| **Theory & Theorems** | CAP Theorem, CALM Theorem, PACELC, Consistent Hashing |
| **Storage Engines** | The LSM-Tree, Bitcask, WiscKey, C-Store (Columnar) |
| **Analytical Systems** | Dremel, Hive, Spark SQL, Madlib |

*(See `/data/raw_pdfs/` for the complete library)*

---

## 📊 Performance Metrics (Projected)

We optimize for three core RAG metrics to ensure authoritative performance:

- **Retrieval Recall@5:** `> 92%` — Ensuring the correct research context is found within the top 5 results.
- **Faithfulness (Groundedness):** `> 98%` — Measured via RAGAS, ensuring the LLM does not hallucinate beyond the provided papers.
- **Answer Relevancy:** `> 90%` — Ensuring technical depth matches the user's intent.

---

## 🛠️ Tech Stack & DevOps

- **Data Pipeline:** Python 3.9+
- **Document Preprocessor:** Docling
- **API Backend:** Python (gRPC / Protocol Buffers)
- **Frontend UI:** Angular
- **Cloud:** AWS (S3 for raw PDFs, Lambda for processing, OpenSearch for Vector Search)
- **CI/CD:** Automated testing and deployment pipelines via GitHub Actions/Terraform.
- **Infrastructure as Code (IaC):** Managed via `/infra/terraform`.

---

## 🛠️ Getting Started

### Prerequisites
- Python 3.9+
- AWS CLI configured
- Docker (optional, for local vector store)

### Installation
```bash
git clone https://github.com/your-repo/database-development-rag.git
cd database-development-rag
pip install -r requirements.txt
```

### Ingestion Pipeline
To parse the current PDF library and update the vector store:
```bash
python scripts/download_files.py
python services/ingestion/pdf_parser.py
```
`pdf_parser.py` should run the Docling-based preprocessing path before chunking/embedding.

---

## 📄 Documentation

- `docs/rag-tools-and-plugins-integration.md` — comprehensive RAG tools/plugins integration guide with step-by-step setup.
- `docs/aws-mlops-pipeline-for-rag.md` — AWS MLOps architecture and execution playbook for this RAG system.

---

## 🛣️ Roadmap
- [ ] **Phase 1:** Data Collection & Parsing (Current)
- [ ] **Phase 2:** Hybrid Search Implementation & Evaluation
- [ ] **Phase 3:** AWS Deployment with automated CI/CD
- [ ] **Phase 4:** UI/UX Interface for interactive research exploration

---

## 🤝 Contribution
Contributions are welcome! Please see the `ai/governance/` directory for rules on adding new papers or modifying the retrieval strategy.
