# Build stage for dependencies
FROM python:3.10-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Consolidated installation: 
# Using --extra-index-url for CPU-only versions of torch and torchvision
# This prevents pip from downloading the full GPU versions (several GBs) 
# when sentence-transformers or docling are installed.
COPY requirements.txt .
RUN pip install --no-cache-dir --user \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    -r requirements.txt torch torchvision

# Final Stage
FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy ONLY installed packages
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# SURGICAL COPY: Only copy what this specific service needs
COPY apps/api_python/ ./apps/api_python/
COPY services/ ./services/
COPY requirements.txt .

EXPOSE 8000

# Package-style run from /app (project root) so absolute `apps.api_python.*` imports resolve.
CMD ["python", "-m", "uvicorn", "apps.api_python.main:app", "--host", "0.0.0.0", "--port", "8000"]
