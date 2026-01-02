#!/bin/bash
# ACGS-2 Test Runner for Development Environment

set -e

echo "🧪 Running ACGS-2 Tests..."

# Check if services are running
if ! docker-compose -f docker-compose.dev.yml ps | grep -q "Up"; then
    echo "❌ Development environment is not running. Start it with: ./scripts/start-dev.sh"
    exit 1
fi

# Run API tests in the agent-bus container
echo "🏃 Running API tests in agent-bus container..."
docker-compose -f docker-compose.dev.yml exec -T agent-bus bash -c "
    cd /app &&
    python -m pytest test_api.py -v --tb=short
"

# Run integration tests that require external services
echo "🔗 Running integration tests..."
docker-compose -f docker-compose.dev.yml exec -T agent-bus bash -c "
    cd /app &&
    python -m pytest test_api.py::TestAPIGatewayIntegration -v --tb=short
"

echo "✅ Tests completed."
