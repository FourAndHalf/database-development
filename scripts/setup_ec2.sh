#!/bin/bash
# EC2 Setup Script for Data Repopulation
set -e

echo "--- Starting EC2 Environment Setup ---"

# 1. Update and install system dependencies
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip libpq-dev build-essential

# 2. Create and activate virtual environment
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "Created virtual environment."
fi
source .venv/bin/activate

# 3. Install dependencies
echo "Installing dependencies from requirements.txt..."
pip install --upgrade pip
pip install -r requirements.txt

# 4. Ensure data directories exist
mkdir -p data/parsed data/chromadb data/raw_pdfs

echo "--- Setup Complete ---"
echo "You can now run the repopulation script with:"
echo "source .venv/bin/activate && python3 scripts/repopulate_from_s3.py"
