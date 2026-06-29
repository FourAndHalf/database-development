# Self-Hosted Infrastructure Guide

This project supports a fully self-hosted deployment using **ChromaDB** (embedded) for vector storage.

## 1. Prerequisites
- Docker and Docker Compose installed.

## 2. Infrastructure Setup
The core services are defined in `docker-compose.yml`:
- **caddy**: SSL termination & routing.
- **postgres**: user, chat, and paper metadata.
- **python-rag-engine**: FastAPI RAG service with the embedded ChromaDB vector store.
- **go-api-gateway**: API gateway.
- **angular-ui**: frontend.

### Starting the Infrastructure
```bash
docker compose up -d
```

## 3. Configuring the Vector Store
The application uses **ChromaDB** in embedded mode — there is no separate vector-database container to run. Vectors persist to a local directory (mounted into the Python service). Configure the path in your `.env` file:

```env
CHROMA_DB_PATH=data/chromadb
```

## 4. Data Durability & Reliability

To ensure your data survives system outages, network issues, or server reboots, we use a three-tier durability strategy:

### A. Auto-Recovery (Restart Policies)
Every core service is configured with `restart: always`. If the server reboots or a process crashes, Docker will automatically bring the database and application back online as soon as the system is ready.

### B. Persistent Storage (Volumes)
Postgres data is stored in a host-mounted volume (`./data/postgres`), and the ChromaDB vector store persists to `./data/chromadb`. This ensures that even if you delete or update the containers, the actual database files remain safe on the host's disk.

### C. Off-site Backups (S3 Integration)
Run `./scripts/backup_db.sh` to back up Postgres off-site:
1.  It triggers a `pg_dump` of your PostgreSQL database.
2.  It uploads the SQL snapshot to your **S3 bucket** (under `/backups/db/`).
3.  Even if your entire server hardware fails, you can recreate the database from these S3 snapshots.

Schedule it via `cron` for automated backups, e.g. a nightly entry:
```cron
0 3 * * * /path/to/project/scripts/backup_db.sh
```

## 5. Cost-Effectiveness
By self-hosting with an embedded vector store, you avoid the costs of:
- AWS OpenSearch Serverless (Minimum ~ $100-200/month).
- Managed Vector DBs (Pinecone, etc.).

Your only cost is the compute (EC2 instance or your own local machine).
