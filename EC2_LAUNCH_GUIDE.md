# AWS EC2 Launch Guide

This guide explains how to deploy this RAG application on a **single AWS EC2 instance** using Docker Compose and a Caddy reverse proxy.

## Stack Overview

| Service           | Image / Source              | Role                          |
|-------------------|-----------------------------|-------------------------------|
| `caddy`           | `caddy:2-alpine`            | SSL termination & routing     |
| `postgres`        | `postgres:15-alpine`        | User, chat, paper metadata DB |
| `qdrant`          | `qdrant/qdrant:v1.9.0`      | Vector search                 |
| `python-rag-engine` | local build               | FastAPI RAG (Groq Llama)      |
| `go-api-gateway`  | local build                 | API gateway                   |
| `angular-ui`      | local build                 | Frontend                      |
| `jenkins`         | `jenkins/jenkins:lts`       | CI/CD                         |
| `smee`            | `ghcr.io/probot/smee-client`| GitHub webhook relay          |

---

## 1. EC2 Instance Sizing

| Tier           | Instance Type      | vCPU | RAM   | Notes                              |
|----------------|--------------------|------|-------|------------------------------------|
| **Minimum**    | `t3.large`         | 2    | 8 GB  | Must enable 4 GB swap              |
| **Recommended**| `c7i-flex.large`   | 2    | 8 GB  | Better CPU for build steps         |
| **Comfortable**| `t3.xlarge`        | 4    | 16 GB | No swap needed; faster builds      |

> [!IMPORTANT]
> The Python RAG engine pulls `sentence-transformers` + CPU-only PyTorch. On a cold build this uses ~6–7 GB RAM. **Always enable swap** on instances with 8 GB or less.

---

## 2. AWS Security Group Rules

Only open these ports on your EC2 Security Group:

| Port  | Source        | Purpose                       |
|-------|---------------|-------------------------------|
| `22`  | Your IP only  | SSH access                    |
| `80`  | `0.0.0.0/0`  | HTTP (Caddy redirects to HTTPS) |
| `443` | `0.0.0.0/0`  | HTTPS (Caddy-managed SSL)     |

> [!CAUTION]
> **Do NOT open** Postgres (`5432`/`5435`), Qdrant (`6333`), or the Go API (`8080`) ports to the internet. All internal services are protected behind Caddy on the Docker network.

---

## 3. Domain & DNS Setup (DuckDNS)

1. Go to [duckdns.org](https://www.duckdns.org) and log in.
2. Create/select the domain `aether-rag-pipeline` (or your own subdomain).
3. Set its IP to your EC2 Elastic IP address.
4. Run this on the EC2 instance to keep the IP updated (replace `YOUR_TOKEN`):
   ```bash
   echo url="https://www.duckdns.org/update?domains=aether-rag-pipeline&token=YOUR_TOKEN&ip=" | curl -K -
   ```
5. (Optional) Add a cron job to keep it fresh:
   ```bash
   (crontab -l 2>/dev/null; echo "*/5 * * * * echo url=\"https://www.duckdns.org/update?domains=aether-rag-pipeline&token=YOUR_TOKEN&ip=\" | curl -s -K - > /dev/null") | crontab -
   ```

> Caddy will automatically obtain a free Let's Encrypt SSL certificate once the domain resolves to your EC2 IP.

---

## 4. Server Initialization

### A. Install Docker

```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-v2
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
newgrp docker        # activate group without logout
```

### B. Enable 4 GB Swap Space *(critical for ≤ 8 GB RAM instances)*

```bash
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile swap swap defaults 0 0' | sudo tee -a /etc/fstab
```

### C. Create Required Data Directories

```bash
cd ~/database-development   # project root
mkdir -p uploads backups
mkdir -p data/{postgres,qdrant,jenkins_home}
mkdir -p data/caddy/{data,config,logs}
```

---

## 5. Configuration

```bash
cp .env.example .env
nano .env   # fill in all your real values
```

**Minimum required values in `.env`:**

```ini
POSTGRES_PASSWORD=some_strong_password   # used by both postgres and go-api-gateway
GROQ_API_KEY=gsk_...
GEMINI_API_KEY=...
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_S3_BUCKET_NAME=...
SMEE_URL=https://smee.io/your-channel-id
```

> [!WARNING]
> Never commit your real `.env` file. It is already in `.gitignore`.

---

## 6. Deploy (Two Methods)

### Method A — Automated (recommended)

```bash
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

This script installs Docker, configures swap, creates directories, validates `.env`, builds images in parallel, and starts everything.

### Method B — Manual

```bash
# Pull pre-built images (postgres, qdrant, caddy, jenkins)
docker compose pull caddy postgres qdrant jenkins

# Build application images in parallel
docker compose build --parallel python-rag-engine go-api-gateway angular-ui

# Start everything
docker compose up -d

# Watch startup progress
docker compose logs -f
```

---

## 7. Accessing Your Services

Once deployed and DNS is pointing to your EC2 IP:

| Service    | URL                                              |
|------------|--------------------------------------------------|
| App UI     | `https://aether-rag-pipeline.duckdns.org`        |
| API Health | `https://aether-rag-pipeline.duckdns.org/healthz`|
| Jenkins    | `https://aether-rag-pipeline.duckdns.org/jenkins`|

**Jenkins initial admin password:**
```bash
docker exec rag-jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

---

## 8. Day-2 Operations

```bash
# View all service status
docker compose ps

# Monitor memory usage
docker stats

# View logs for a specific service
docker compose logs -f go-api-gateway

# Manual DB backup to S3
./scripts/backup_db.sh

# Pull latest code and redeploy
git pull
docker compose build --parallel python-rag-engine go-api-gateway angular-ui
docker compose up -d --no-deps python-rag-engine go-api-gateway angular-ui

# Stop everything (data is preserved in ./data/)
docker compose down
```

---

## 9. Troubleshooting Common Startup Failures

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| `go-api-gateway` exits immediately | Postgres not ready | Check `docker compose ps` — postgres needs to be `healthy` first. Healthchecks ensure this automatically. |
| `python-rag-engine` OOM killed | Not enough RAM | Enable swap (Section 4B) or upgrade instance. |
| Caddy fails to get SSL cert | DNS not resolving yet | Wait 1–5 min after updating DuckDNS. Port 80/443 must be open in Security Group. |
| `smee` container keeps restarting | `SMEE_URL` not set in `.env` | Set a real Smee.io channel URL in `.env`. |
| `qdrant` unhealthy | Slow startup | Normal on cold start — healthcheck retries for 30 s × 5 times. |
