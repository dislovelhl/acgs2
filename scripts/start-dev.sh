#!/bin/bash
# ACGS-2 Development Environment Startup Script

set -e

echo "🚀 Starting ACGS-2 Development Environment..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📋 Creating .env file from template..."
    cp .env.dev .env
    echo "✅ Created .env file. You may want to review and modify the configuration."
fi

# Build and start services
echo "🏗️  Building and starting services..."
docker-compose -f docker-compose.dev.yml up --build -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check service health
echo "🔍 Checking service health..."

# Function to check service health
check_service() {
    local service=$1
    local url=$2
    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "$url" > /dev/null 2>&1; then
            echo "✅ $service is ready"
            return 0
        fi
        echo "⏳ Waiting for $service... (attempt $attempt/$max_attempts)"
        sleep 2
        ((attempt++))
    done

    echo "❌ $service failed to start"
    return 1
}

# Check services
check_service "OPA" "http://localhost:8181/health"
check_service "Redis" "http://localhost:6379" || echo "⚠️  Redis health check skipped (no HTTP endpoint)"
check_service "API Gateway" "http://localhost:8080/health"
check_service "Agent Bus" "http://localhost:8000/health" || echo "⚠️  Agent Bus health check may not be available yet"

echo ""
echo "🎉 ACGS-2 Development Environment Started!"
echo ""
echo "📋 Services:"
echo "   • API Gateway: http://localhost:8080"
echo "   • Agent Bus:   http://localhost:8000"
echo "   • OPA:         http://localhost:8181"
echo "   • Redis:       localhost:6379"
echo "   • Kafka:       localhost:9092"
echo ""
echo "📖 Useful commands:"
echo "   • View logs:    docker-compose -f docker-compose.dev.yml logs -f"
echo "   • Stop:         docker-compose -f docker-compose.dev.yml down"
echo "   • Restart:      docker-compose -f docker-compose.dev.yml restart"
echo "   • Clean up:     docker-compose -f docker-compose.dev.yml down -v"
echo ""
echo "🧪 Run tests:"
echo "   • All tests:    ./scripts/run-tests.sh"
echo "   • Quick test:   docker-compose -f docker-compose.dev.yml exec agent-bus python -m pytest tests/ -v --tb=short"
