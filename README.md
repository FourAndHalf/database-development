# 🗄️ Database Research RAG System

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Go 1.23+](https://img.shields.io/badge/go-1.23+-00ADD8.svg)](https://golang.org/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Angular 20](https://img.shields.io/badge/Angular-20-DD0031.svg)](https://angular.io/)

A scalable Retrieval-Augmented Generation (RAG) system designed to index, query, and synthesize information from foundational database research papers. By leveraging modern microservices, it bridges the gap between raw academic research and actionable engineering insights.

## 🚀 Overview

This project serves as a "living encyclopedia" for database engineering. Built on a multi-language microservices architecture, it processes dense academic PDFs using Docling, stores embeddings in ChromaDB, and uses high-performance API gateways to serve a modern Angular frontend.

---

## 🏛️ Current Architecture Design

The project uses a containerized, decoupled microservices architecture designed for high precision and scalability.

### 1. Presentation Layer (UI)
- **Angular UI (`/apps/ui`):** A modern, responsive web frontend built with **Angular (v20)**. It serves as the primary interface for users to submit research queries, explore papers, and view AI-generated, citation-backed answers. It is served behind an **Nginx** reverse proxy in production.

### 2. API Gateway & Core Backend (Go)
- **Go API Gateway (`/apps/api`):** A high-throughput REST API written in **Go 1.23**. It acts as the central orchestrator, handling:
  - User Authentication (JWT-based).
  - Rate Limiting and Telemetry (Prometheus).
  - Request orchestration between the UI, the PostgreSQL database, and the Python RAG Engine.
  - PostgreSQL interaction for managing user metadata, chat history, and document states.

### 3. RAG Engine & AI Services (Python)
- **FastAPI Service (`/apps/api/main.py`):** A Python-based AI service responsible for the heavy lifting of the RAG pipeline.
  - **Ingestion & Parsing:** Uses **Docling** for high-fidelity extraction of text, tables, and citations from academic PDFs.
  - **Embedding:** Utilizes local **Sentence-Transformers** (e.g., `BAAI/bge-small-en-v1.5`) to generate dense semantic vectors, avoiding expensive API calls for high-volume ingestion.
  - **Vector Storage:** Stores and queries embeddings using **ChromaDB**.
  - **LLM Integration:** Combines retrieved contexts with powerful prompts to generate grounded answers using external LLM APIs (e.g., OpenAI, Anthropic).

### 4. Data & Storage Layer
- **PostgreSQL (15):** Relational database managing application state (users, auth, chat logs).
- **ChromaDB:** Local vector database storing embedded document chunks for semantic search.
- **Local File System:** Manages raw PDFs, parsed JSONs, and embedding artifacts in the `/data` directory.

---

## ⚙️ How It Works

1. **Document Ingestion (`scripts/` & `services/ingestion/`):** Raw PDFs of research papers are downloaded into `/data/raw_pdfs`. The system uses Docling to accurately parse the structure (headings, paragraphs, tables) and convert them to parsed JSON representations.
2. **Chunking & Embedding:** The parsed documents are broken down into semantically meaningful chunks (Hierarchical Chunking). The Python engine uses a local Sentence-Transformer model to convert these text chunks into dense numeric vectors.
3. **Vector Storage:** The vectors, along with metadata (paper title, chunk index), are stored in ChromaDB for rapid similarity search.
4. **Query Execution:** 
   - A user submits a query via the **Angular UI**.
   - The **Go API Gateway** authenticates the user, logs the query in PostgreSQL, and forwards the request to the **Python RAG Engine**.
   - The Python engine embeds the user's query, performs a semantic search against ChromaDB to find the most relevant document chunks, and optionally reranks them.
   - The retrieved context is formatted into a strict prompt and sent to an LLM to generate a grounded, cited response.
   - The answer is streamed back through the Go Gateway to the UI.

---

## 💻 Installation & Setup

You can run the entire multi-service application locally using Docker Compose.

### Prerequisites
- **Docker** & **Docker Compose**
- **Git**
- (Optional) **Python 3.9+** and **Go 1.23+** if running services manually outside of Docker.

### Local Deployment Steps

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/your-org/database-development.git
   cd database-development
   ```

2. **Configure Environment Variables:**
   Copy the example environment file and adjust any keys (like external LLM API keys if required by the python service).
   ```bash
   cp configs/service.env.example .env
   ```

3. **Start the Infrastructure via Docker Compose:**
   This command will build the Go API, Python RAG Engine, and Angular UI containers, and spin up PostgreSQL.
   ```bash
   docker-compose up --build -d
   ```

4. **Verify the Services:**
   Check that all containers are running successfully:
   ```bash
   docker-compose ps
   ```

### Accessing the Application
Once the containers are up and running, you can access the different layers of the system:

- **Frontend UI:** [http://localhost:4200](http://localhost:4200)
- **Go API Gateway:** [http://localhost:8081](http://localhost:8081)
- **Python RAG Engine:** [http://localhost:8000](http://localhost:8000)
- **PostgreSQL Database:** `localhost:5434` (Credentials specified in `docker-compose.yml`)

---

## 🛑 Stopping the System

To gracefully stop and remove the containers:
```bash
docker-compose down
```
*(Note: If you want to wipe the database and vector store volumes, run `docker-compose down -v`)*

---

## 📚 Further Documentation

- `/docs`: Contains advanced integration playbooks and AWS deployment strategies.
- `/ai`: Contains system prompts, governance rules, and prompt engineering evaluation details.
- `/experiments`: Scripts used for evaluating chunking, embedding models, and reranking strategies.
