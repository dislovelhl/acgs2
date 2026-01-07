#!/bin/bash
# ACGS-2 Governance Service Staging Deployment Script
# Constitutional Hash: cdd01ef066bc6cf2

set -e

echo "🚀 Starting Governance Service Staging Deployment..."

# Navigate to project root
cd "$(dirname "$0")/.."

# 1. Build and Start Services
echo "🏗️  Building stability-enhanced governance service..."
docker compose -f docker-compose.staging.yml build --no-cache

echo "🚢 Deploying to staging..."
docker compose -f docker-compose.staging.yml up -d

# 2. Wait for Health Check
echo "⏳ Waiting for service to become healthy..."
MAX_RETRIES=12
COUNT=0
until [ $(docker inspect -f '{{.State.Health.Status}}' acgs2-agent-bus-1 2>/dev/null || echo "unhealthy") == "healthy" ]; do
    if [ $COUNT -ge $MAX_RETRIES ]; then
        echo "❌ Deployment failed: Service unhealthy after $MAX_RETRIES attempts."
        docker compose -f docker-compose.staging.yml logs agent-bus
        exit 1
    fi
    echo -n "."
    sleep 5
    COUNT=$((COUNT+1))
done

echo -e "\n✅ Governance Service is healthy in Staging!"
echo "🔗 API Base: http://localhost:8100"
echo "📊 Stability Metrics Endpoint: http://localhost:8100/governance/stability/metrics"

# 3. Verify Rust Kernel Integration
echo "🧪 Verifying Rust performance kernel..."
if docker compose -f docker-compose.staging.yml logs agent-bus | grep -q "mHC: Using Rust performance kernel"; then
    echo "⚡ Rust optimized kernel confirmed active."
else
    echo "⚠️  Warning: Rust kernel not found in logs. Check build steps."
fi

echo "✨ Deployment Complete."
