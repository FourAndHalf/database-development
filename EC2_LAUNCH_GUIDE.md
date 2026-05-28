# AWS EC2 Launch Guide

This guide explains what is needed to launch this project on a single AWS EC2 instance using Docker Compose.

The project is a containerized RAG application with these main parts:

- Angular UI served by Nginx.
- Go API gateway on port `8080`.
- Python FastAPI RAG engine on port `8000` inside the Docker network.
- PostgreSQL for users, chats, papers, and metadata.
- Qdrant for vector search.
- Optional Jenkins service for self-hosted CI/CD.
- Optional S3 integration for PDF artifacts and database backups.

## 1. Current Launch Blockers In This Repository

Before launching on EC2, fix these repository mismatches. They are visible in the current tree and will stop a clean Docker Compose launch.

### Docker Compose Python Dockerfile Path

`docker-compose.yml` currently points at:

```yaml
dockerfile: apps/api_python/Dockerfile.python
```

The current directory is:

```text
apps/api-python/Dockerfile.python
```

Use:

```yaml
dockerfile: apps/api-python/Dockerfile.python
```

### Python Import Path

The Python service files are under `apps/api-python`, but code imports `apps.api_python_python`, for example:

```python
from apps.api_python_python import state
from apps.api_python_python.routers import query, papers
```

Python package imports cannot use a hyphenated directory name. Pick one naming convention before deployment:

- Recommended: rename `apps/api-python` to `apps/api_python`, then update Docker Compose to `apps/api_python/Dockerfile.python`.
- Alternative: keep the folder as `api-python`, but create a valid Python package path and update all imports.

The simplest operational path is to use `apps/api_python` everywhere.

### Go Dockerfile Paths

`apps/api-go/Dockerfile.go` currently refers to `apps/api-go-go`, but the real directory is `apps/api-go`.

Replace references like:

```dockerfile
COPY apps/api-go-go/go.mod apps/api-go-go/go.sum ./apps/api-go-go/
WORKDIR /app/apps/api-go-go
COPY apps/api-go-go/ ./apps/api-go-go/
```

with:

```dockerfile
COPY apps/api-go/go.mod apps/api-go/go.sum ./apps/api-go/
WORKDIR /app/apps/api-go
COPY apps/api-go/ ./apps/api-go/
```

Also make sure the binary is copied from `/app/apps/api-go/main`.

### Go RAG Engine Value

The Go API currently supports `RAG_ENGINE=chroma` for calling the Python service. `docker-compose.yml` sets:

```env
RAG_ENGINE=qdrant
```

That falls through to the mock engine in the Go code. Use:

```env
RAG_ENGINE=chroma
```

The Python service can still use Qdrant internally with:

```env
VECTOR_BACKEND=qdrant
QDRANT_HOST=qdrant
QDRANT_PORT=6333
```

### Python Dependencies

`requirements.txt` currently does not list everything imported by `apps/api-python/main.py` and routers. Add or verify these packages before building:

```text
torch
transformers
accelerate
bitsandbytes
prometheus-fastapi-instrumentator
arize-phoenix
openinference-instrumentation
duckduckgo-search
```

`bitsandbytes` and `device_map="auto"` are sensitive to CPU/GPU environments. If you launch on CPU-only EC2, test this path carefully or remove 4-bit quantization and use a smaller CPU-safe model path.

### Health Check URL

The Go service exposes:

```text
GET /healthz
```

Use `/healthz`, not `/health`, in verification commands.

## 2. Recommended EC2 Shape

Use at least:

- Development/smoke test: `t3.large` or `t3.xlarge`, 30-60 GB gp3 EBS.
- CPU-only local model testing: `c7i.xlarge` or larger, 80-120 GB gp3 EBS, 8-16 GB RAM minimum.
- GPU-backed local LLM: `g5.xlarge` or larger.

The Python service loads local Hugging Face models at startup. A small 2 vCPU / 4 GB RAM instance can run Docker, Postgres, Qdrant, and the UI, but it is likely to fail or swap heavily when loading local LLMs. If you want a low-cost EC2 deployment, use the Go API, Postgres, Qdrant, and UI on EC2, then change the Python generation path to call an external hosted LLM instead of loading local models.

## 3. AWS Resources To Create

### EC2 Instance

Use Ubuntu Server 22.04 LTS or 24.04 LTS.

Recommended settings:

- AMI: Ubuntu Server LTS.
- Instance type: choose from the sizing notes above.
- Storage: at least 60 GB gp3 for Docker images, model cache, database volume, and vector data.
- Key pair: create or choose an SSH key.
- IAM role: attach a role with S3 permissions if you use backups or S3 paper storage.

### Security Group

Open only what you need:

| Port | Source | Purpose |
| --- | --- | --- |
| `22` | Your IP only | SSH |
| `80` | `0.0.0.0/0` | HTTP UI |
| `443` | `0.0.0.0/0` | HTTPS UI, if configured |
| `8081` | Your IP only | Jenkins, optional |
| `6333` | Your IP only or closed | Qdrant dashboard/API, optional |

Do not expose Postgres (`5434`) publicly. Do not expose the Python service publicly. The Angular Nginx container proxies UI API calls to the Go gateway over the internal Docker network.

### S3 Bucket

Create one bucket if you want off-instance backups or artifact storage:

```text
s3://your-rag-bucket-name
```

Suggested prefixes:

```text
raw_pdfs/
parsed/
chunks/
embeddings/
backups/db/
```

### IAM Role

Prefer an EC2 instance role over static AWS keys. Minimum S3 permissions should be scoped to your bucket:

- `s3:ListBucket`
- `s3:GetObject`
- `s3:PutObject`
- `s3:DeleteObject`, only if the app needs deletion

## 4. Bootstrap The EC2 Host

SSH into the instance:

```bash
ssh -i /path/to/key.pem ubuntu@YOUR_EC2_PUBLIC_IP
```

Install base packages:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl git unzip awscli htop
```

Install Docker:

```bash
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo tee /etc/apt/keyrings/docker.asc >/dev/null
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker "$USER"
```

Log out and back in so the `docker` group takes effect.

Verify:

```bash
docker version
docker compose version
```

For small instances, add swap:

```bash
sudo fallocate -l 8G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile swap swap defaults 0 0' | sudo tee -a /etc/fstab
free -h
```

## 5. Clone And Configure The Project

Clone the repository:

```bash
git clone YOUR_REPOSITORY_URL database-development
cd database-development
```

Create `.env`:

```bash
cp configs/service.env.example .env
```

Use values like these for EC2:

```env
ENVIRONMENT=production

DB_URL=postgres://nexus:CHANGE_ME_STRONG_PASSWORD@postgres:5432/nexus_db?sslmode=disable

VECTOR_BACKEND=qdrant
QDRANT_HOST=qdrant
QDRANT_PORT=6333

AWS_REGION=us-east-1
AWS_S3_BUCKET_NAME=your-rag-bucket-name

UI_ORIGIN=http://YOUR_DOMAIN_OR_EC2_PUBLIC_IP
PYTHON_SERVICE_URL=http://python-rag-engine:8000
```

Also update `docker-compose.yml` so the Postgres password and the Go `DB_URL` use the same strong password.

For production, do not commit `.env`.

## 6. Production-Oriented Compose Notes

At minimum, the public service should be the Angular/Nginx container on host port `80`:

```yaml
angular-ui:
  ports:
    - "80:80"
```

The Go API does not need a public host port if the UI Nginx proxies `/v1/` and `/healthz` internally. You can keep it internal unless you need direct API testing from outside the host.

Avoid publishing these ports publicly in production:

- Postgres: `5432` or `5434`
- Python RAG service: `8000`
- Qdrant: `6333`, unless restricted to your IP

The current compose file includes Jenkins. If you do not need Jenkins on the EC2 host, disable it to save memory:

```bash
docker compose up -d postgres qdrant python-rag-engine go-api-gateway angular-ui
```

## 7. Build And Launch

After fixing the blockers listed in section 1:

```bash
docker compose build
docker compose up -d
```

Check containers:

```bash
docker compose ps
```

Watch logs:

```bash
docker compose logs -f go-api-gateway
docker compose logs -f python-rag-engine
docker compose logs -f angular-ui
```

Verify from the EC2 host:

```bash
curl -i http://localhost/healthz
curl -i http://localhost/v1/papers
```

Verify from your browser:

```text
http://YOUR_DOMAIN_OR_EC2_PUBLIC_IP
```

## 8. Data And Ingestion

The compose file mounts:

```yaml
./data:/app/data
```

Keep the repository's `data/` directory on persistent EBS storage. For a single-instance deployment, this is where raw PDFs, parsed files, chunks, and local artifacts can live.

Expected local data folders:

```text
data/raw_pdfs/
data/parsed/
data/chunks/
data/embeddings/
```

Qdrant and Postgres use named Docker volumes:

```text
pgdata
qdrant_data
```

Do not run `docker compose down -v` unless you intentionally want to delete database and vector-store data.

## 9. Backups

The repo includes:

```text
scripts/backup_db.sh
```

It dumps the `nexus_postgres` database and uploads to:

```text
s3://${AWS_S3_BUCKET_NAME}/backups/db/
```

Test it after launch:

```bash
chmod +x scripts/backup_db.sh
./scripts/backup_db.sh
```

Add a cron job for nightly backups:

```bash
crontab -e
```

Example:

```cron
0 2 * * * cd /home/ubuntu/database-development && ./scripts/backup_db.sh >> /var/log/rag-db-backup.log 2>&1
```

You should also snapshot the EC2 EBS volume or back up Qdrant separately if the vector index cannot be regenerated quickly.

## 10. Jenkins Optional Setup

If you keep Jenkins enabled, open:

```text
http://YOUR_EC2_PUBLIC_IP:8081
```

Get the initial admin password:

```bash
docker exec rag-jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

The current `Jenkinsfile` also references `apps/api_python/`. Make that path match the final Python package directory before relying on the pipeline.

For a small EC2 instance, Jenkins can consume significant memory. It is better to disable Jenkins until the application stack is stable.

## 11. HTTPS And Domain

For a real public deployment, point a DNS record at the EC2 public IP:

```text
A record: rag.example.com -> YOUR_EC2_PUBLIC_IP
```

Common options for TLS:

- Put an AWS Application Load Balancer with ACM certificate in front of EC2.
- Install Caddy or Nginx Proxy Manager on the host and terminate TLS there.
- Use Certbot with a host-level Nginx reverse proxy.

If you add a host-level reverse proxy, keep Docker's Angular UI bound to an internal or alternate host port, then proxy public `443` to it.

## 12. Operational Commands

Update code and redeploy:

```bash
git pull
docker compose build
docker compose up -d
```

Restart one service:

```bash
docker compose restart go-api-gateway
```

Show resource usage:

```bash
docker stats
```

Show service logs:

```bash
docker compose logs --tail=200 python-rag-engine
```

Stop the stack without deleting data:

```bash
docker compose down
```

Stop the stack and delete volumes:

```bash
docker compose down -v
```

Only use `down -v` when you intentionally want to remove Postgres, Qdrant, and Jenkins persisted data.

## 13. Troubleshooting

### Docker Build Cannot Find Files

Check the paths in:

- `docker-compose.yml`
- `apps/api-go/Dockerfile.go`
- `apps/api-python/Dockerfile.python`

The current repo contains path mismatches, so fix those before launching.

### Python Service Fails On Import

If logs show `ModuleNotFoundError` for `apps.api_python_python`, normalize the Python directory and imports. Use a valid Python package directory such as:

```text
apps/api_python/
```

Then update imports to:

```python
from apps.api_python import state
from apps.api_python.routers import query, papers
```

### Python Service Runs Out Of Memory

Symptoms:

- Container restarts repeatedly.
- `docker compose logs python-rag-engine` shows model loading stops partway.
- `docker stats` shows memory near the limit.

Fixes:

- Use a larger EC2 instance.
- Use GPU-backed EC2 for local model inference.
- Remove or reduce local LLM loading.
- Use an external hosted LLM API.
- Increase swap as a temporary development workaround.

### UI Loads But Chat Fails

Check:

```bash
curl -i http://localhost/healthz
docker compose logs --tail=100 go-api-gateway
docker compose logs --tail=100 python-rag-engine
```

Common causes:

- `RAG_ENGINE` is set to `qdrant` instead of `chroma`.
- `PYTHON_SERVICE_URL` is wrong.
- Python service is still loading models.
- Python service failed to connect to Qdrant.

### Qdrant Has No Results

The app can launch with an empty Qdrant collection, but queries will not return useful paper context until ingestion has populated vectors.

Check Qdrant logs:

```bash
docker compose logs --tail=100 qdrant
```

Check the Python service startup logs for the vector-store count.

## 14. Launch Checklist

- EC2 instance created with enough CPU, RAM, and disk.
- Security group exposes only SSH, HTTP/HTTPS, and any restricted admin ports.
- IAM role attached for S3 access.
- Docker and Docker Compose installed.
- Swap configured if using a small instance.
- Repository cloned.
- `.env` created and secrets changed.
- Dockerfile and import path mismatches fixed.
- `RAG_ENGINE=chroma` for the Go API.
- `VECTOR_BACKEND=qdrant` for the Python service.
- `docker compose build` succeeds.
- `docker compose up -d` starts all required services.
- `curl http://localhost/healthz` returns a healthy response.
- Browser can reach the UI.
- Database backup to S3 has been tested.
- EBS snapshot or equivalent recovery plan exists.
