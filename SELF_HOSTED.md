# Self-Hosted Infrastructure Guide

This project supports a fully self-hosted deployment using **Qdrant** for vector storage and **Jenkins** for CI/CD.

## 1. Prerequisites
- Docker and Docker Compose installed.
- (Optional) A target server with Docker for Jenkins to deploy to.

## 2. Infrastructure Setup
The `docker-compose.yml` has been updated to include:
- **Qdrant**: Available on ports `6333` (HTTP) and `6334` (gRPC).
- **Jenkins**: Available on port `8081`. It is configured with access to the host's Docker socket to allow building project containers.

### Starting the Infrastructure
```bash
docker compose up -d qdrant jenkins postgres
```

## 3. Configuring Qdrant
To switch the application to use Qdrant instead of ChromaDB, set the following environment variables in your `.env` file:

```env
VECTOR_BACKEND=qdrant
QDRANT_HOST=qdrant
QDRANT_PORT=6333
```

## 4. Setting up Jenkins
1.  Open `http://localhost:8081` in your browser.
2.  Retrieve the initial admin password from the Jenkins container:
    ```bash
    docker exec rag-jenkins cat /var/jenkins_home/secrets/initialAdminPassword
    ```
3.  Install suggested plugins.
4.  Create a new **Pipeline** job.
5.  Configure the job to use "Pipeline script from SCM" and point it to your repository.
6.  Jenkins will automatically detect the `Jenkinsfile` and start the build.

### CI/CD Pipeline Stages
- **Checkout**: Pulls the latest code.
- **Lint**: Runs `flake8` for Python and `go vet` for Go.
- **Build**: Builds all project containers using Docker Compose.
- **Test**: Spins up Qdrant and Postgres in a temporary environment to run integration tests.
- **Deploy**: (On `main` branch) Deploys the updated containers.

## 5. Data Durability & Reliability

To ensure your data survives system outages, network issues, or server reboots, we have implemented a three-tier durability strategy:

### A. Auto-Recovery (Restart Policies)
Every core service (`postgres`, `qdrant`, `jenkins`, `api`) is configured with `restart: always`. If the server reboots or a process crashes, Docker will automatically bring the database and application back online as soon as the system is ready.

### B. Persistent Storage (Volumes)
Data is stored in **Named Docker Volumes** (`pgdata`, `qdrant_data`). This ensures that even if you delete or update the containers, the actual database files remain safe on the host's disk.

### C. Off-site Backups (S3 Integration)
The Jenkins pipeline includes a **Backup Database** stage.
1.  It triggers a `pg_dump` of your PostgreSQL database.
2.  It automatically uploads the encrypted SQL snapshot to your **S3 bucket** (under `/backups/db/`).
3.  Even if your entire server hardware fails, you can recreate the entire database from these S3 snapshots.

### Running a Manual Backup
You can trigger a backup manually at any time:
```bash
./scripts/backup_db.sh
```

## 6. Cost-Effectiveness
...
By self-hosting Qdrant and Jenkins, you avoid the costs of:
- AWS OpenSearch Serverless (Minimum ~ $100-200/month).
- GitHub Actions paid minutes (Free for public repos, but limited for private).
- Managed Vector DBs (Pinecone, etc.).

Your only cost is the compute (EC2 instance or your own local machine).
