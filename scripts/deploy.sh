#!/usr/bin/env bash
# =============================================================================
# scripts/deploy.sh — One-command EC2 bootstrap & deployment for this project.
#
# Usage (on a fresh EC2 Ubuntu instance):
#   git clone <repo-url> database-development
#   cd database-development
#   chmod +x scripts/deploy.sh
#   ./scripts/deploy.sh
#
# What this does:
#   1. Installs Docker + Docker Compose plugin (if not present)
#   2. Adds current user to the docker group
#   3. Creates required data directories
#   4. Configures 4 GB swap space (critical for small instances)
#   5. Validates .env is in place
#   6. Builds and starts all services via docker compose
# =============================================================================

set -euo pipefail

RED='\033[0;31m'; YELLOW='\033[1;33m'; GREEN='\033[0;32m'; NC='\033[0m'
info()    { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }

# ── 0. Guard: must be run from the project root ──────────────────────────────
[[ -f "docker-compose.yml" ]] || error "Run this script from the project root directory."

# ── 1. Install Docker ─────────────────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
  info "Docker not found — installing..."
  sudo apt-get update -qq
  sudo apt-get install -y --no-install-recommends docker.io docker-compose-v2
  sudo systemctl enable --now docker
  sudo usermod -aG docker "$USER"
  warn "Added $USER to the docker group. You may need to log out and back in if this is a fresh install."
  warn "If docker commands fail with permission errors, run: newgrp docker"
else
  info "Docker already installed: $(docker --version)"
fi

# Ensure docker compose plugin / standalone is available
if ! docker compose version &>/dev/null 2>&1; then
  info "Installing docker-compose-v2 plugin..."
  sudo apt-get install -y docker-compose-v2
fi

# ── 2. Create required data directories ──────────────────────────────────────
info "Creating data directories..."
mkdir -p uploads backups
mkdir -p data/{postgres,qdrant,jenkins_home}
mkdir -p data/caddy/{data,config,logs}
chmod 755 uploads backups

# ── 3. Configure swap space (skip if already configured) ─────────────────────
SWAPFILE=/swapfile
if [[ ! -f "$SWAPFILE" ]]; then
  info "Configuring 4 GB swap space..."
  sudo fallocate -l 4G "$SWAPFILE"
  sudo chmod 600 "$SWAPFILE"
  sudo mkswap "$SWAPFILE"
  sudo swapon "$SWAPFILE"
  grep -q "$SWAPFILE" /etc/fstab || echo "$SWAPFILE swap swap defaults 0 0" | sudo tee -a /etc/fstab
  info "Swap configured: $(free -h | grep Swap)"
else
  info "Swap already exists at $SWAPFILE — skipping."
fi

# ── 4. Validate .env ──────────────────────────────────────────────────────────
if [[ ! -f ".env" ]]; then
  warn ".env file not found. Copying from .env.example..."
  cp .env.example .env
  error "Please edit .env with your real credentials, then re-run this script."
fi

# Check critical env vars are not still set to placeholders
REQUIRED_VARS=(POSTGRES_PASSWORD GROQ_API_KEY)
MISSING=()
for var in "${REQUIRED_VARS[@]}"; do
  value=$(grep -E "^${var}=" .env | cut -d= -f2- | tr -d '"' | tr -d "'")
  if [[ -z "$value" || "$value" == *"your-"* || "$value" == "change_me"* ]]; then
    MISSING+=("$var")
  fi
done
if [[ ${#MISSING[@]} -gt 0 ]]; then
  error "The following required variables in .env are still placeholders: ${MISSING[*]}\nPlease set real values and re-run."
fi

# ── 5. Build and start services ───────────────────────────────────────────────
info "Building images and starting services (this may take several minutes on first run)..."
docker compose pull caddy postgres qdrant jenkins 2>/dev/null || true
docker compose build --parallel python-rag-engine go-api-gateway angular-ui
docker compose up -d

# ── 6. Health check ───────────────────────────────────────────────────────────
info "Waiting for services to become healthy (up to 3 minutes)..."
TIMEOUT=180
ELAPSED=0
while [[ $ELAPSED -lt $TIMEOUT ]]; do
  UNHEALTHY=$(docker compose ps --format json 2>/dev/null \
    | python3 -c "import sys,json; data=sys.stdin.read().strip(); \
      services=[json.loads(l) for l in data.splitlines() if l.strip()]; \
      print(sum(1 for s in services if s.get('Health','') in ('starting','unhealthy')))" 2>/dev/null || echo "?")
  
  if [[ "$UNHEALTHY" == "0" ]]; then
    break
  fi
  sleep 5
  ELAPSED=$((ELAPSED + 5))
done

echo ""
info "════════════════════════════════════════"
info "         Deployment Complete!           "
info "════════════════════════════════════════"
echo ""
docker compose ps
echo ""
info "Service URLs (once DNS propagates to this IP):"
echo "  App UI   → https://aether-rag-pipeline.duckdns.org"
echo "  Jenkins  → https://aether-rag-pipeline.duckdns.org/jenkins"
echo "  Health   → https://aether-rag-pipeline.duckdns.org/healthz"
echo ""
info "Jenkins initial password:"
docker exec rag-jenkins cat /var/jenkins_home/secrets/initialAdminPassword 2>/dev/null \
  || warn "Jenkins not ready yet — check with: docker logs rag-jenkins"
echo ""
info "Monitor resources:  docker stats"
info "View logs:          docker compose logs -f [service-name]"
info "Stop everything:    docker compose down"
