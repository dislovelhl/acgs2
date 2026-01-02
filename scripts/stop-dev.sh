#!/bin/bash
# ACGS-2 Development Environment Stop Script

echo "🛑 Stopping ACGS-2 Development Environment..."

# Stop services
docker-compose -f docker-compose.dev.yml down

echo "✅ All services stopped."
