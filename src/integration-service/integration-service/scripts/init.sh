#!/bin/bash
# Environment initialization for ACGS-2 Integration Service
# Set up virtualenv, dependencies, and local configuration

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$SERVICE_ROOT"

echo "🧪 Initializing Integration Service in $SERVICE_ROOT..."

# 1. Create virtual environment
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
fi

# 2. Install/Update dependencies
echo "📥 Installing dependencies..."
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

# 3. Set up environment variables
if [ ! -f ".env" ]; then
    echo "📝 Creating .env from .env.example..."
    cp .env.example .env
    echo "⚠️  Please update .env with your credentials (especially LINEAR_API_KEY for Spec 001)."
fi

# 4. Create necessary local directories
mkdir -p logs data

echo "✅ Initialization complete!"
echo "🚀 To activate the environment, run: source .venv/bin/activate"
