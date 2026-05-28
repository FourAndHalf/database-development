# AWS EC2 Launch Guide

This guide explains what is needed to launch this project on a single AWS EC2 instance using Docker Compose and a **Caddy Reverse Proxy**.

The project is a containerized RAG application with these main parts:

- Angular UI.
- Go API gateway.
- Python FastAPI RAG engine (running Qwen 0.5B/1.5B via Transformers).
- PostgreSQL for users, chats, papers, and metadata.
- Qdrant for vector search.
- Jenkins for self-hosted CI/CD.
- Caddy for SSL and Routing.

## 1. Directory Structure Setup

Before launching, create the following directory structure on your EC2 host (under `/home/ubuntu/database-development/`):

```bash
mkdir -p ~/database-development/{uploads,backups,data}
mkdir -p ~/database-development/data/{postgres,qdrant,models,jenkins_home}
```

This layout ensures that your EBS data is isolated from the application code and survives container updates.

## 2. Security Hardening (The Firewall Rule)

**Do NOT expose internal services.** Your AWS Security Group should only allow:

| Port | Source | Purpose |
| --- | --- | --- |
| `22` | Your IP | SSH Access |
| `80` | `0.0.0.0/0` | Public Web Traffic (UI) |
| `443` | `0.0.0.0/0` | Public Web Traffic (HTTPS) |
| `5435`| Localhost | Docker Postgres (External Access) |

**Note on Postgres:** Since your host already runs Postgres on `5432`, this Docker instance is mapped to host port **`5435`**. Internal Docker services still talk to it via `postgres:5432`.

The internal services (Postgres, Qdrant, API) are protected behind the **Caddy Reverse Proxy** and are only reachable via the internal Docker network.

## 3. Reverse Proxy & Domain Routing

We use Caddy to handle SSL and route traffic to your DuckDNS domain:
- **Domain:** `https://aether-rag-pipeline.duckdns.org`
- **Routing:**
  - `/` -> Angular UI
  - `/api/` -> Go API Gateway
  - `/jenkins` -> Jenkins CI/CD

Caddy will automatically provision an SSL certificate via Let's Encrypt once the domain points to your EC2 IP.

## 4. Server Initialization (The "Must-Dos")
...
### C. Configure DuckDNS
Ensure your DuckDNS token is running on the EC2 instance to keep the IP updated:
```bash
echo url="https://www.duckdns.org/update?domains=aether-rag-pipeline&token=YOUR_TOKEN&ip=" | curl -k -K -
```

### A. Install Docker
```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-v2
sudo usermod -aG docker $USER
```
*(Logout and back in for groups to take effect)*

### B. Enable 4GB Swap Space (CRITICAL for c7i-flex.large)
```bash
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile swap swap defaults 0 0' | sudo tee -a /etc/fstab
```

## 5. Deployment Commands

1.  **Build and Start:**
    ```bash
    docker compose up -d
    ```
2.  **Monitor Memory:**
    ```bash
    docker stats
    ```
3.  **Manual Database Backup:**
    ```bash
    ./scripts/backup_db.sh
    ```

## 6. Accessing Your Services

- **App UI:** `http://[your-ec2-ip]`
- **Jenkins:** `http://[your-ec2-ip]/jenkins`
- **Initial Jenkins Password:**
  `docker exec rag-jenkins cat /var/jenkins_home/secrets/initialAdminPassword`
