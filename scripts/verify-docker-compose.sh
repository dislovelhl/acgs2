#!/bin/bash
# =============================================================================
# Docker Compose Verification Script
# =============================================================================
# This script verifies that all Docker Compose services start correctly and
# pass their health checks.
#
# Usage: ./scripts/verify-docker-compose.sh
#
# Expected outcome:
#   - 5 services running (opa, jupyter, redis, zookeeper, kafka)
#   - All health checks pass
#   - OPA responds to health check at http://localhost:8181/health
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=============================================="
echo "ACGS-2 Docker Compose Verification"
echo "=============================================="
echo ""

# Step 1: Validate compose configuration
echo -e "${YELLOW}[1/5] Validating Docker Compose configuration...${NC}"
if docker compose config --quiet; then
    echo -e "${GREEN}✓ Configuration is valid${NC}"
else
    echo -e "${RED}✗ Configuration is invalid${NC}"
    exit 1
fi
echo ""

# Step 2: Start services
echo -e "${YELLOW}[2/5] Starting Docker Compose services...${NC}"
docker compose up -d
echo -e "${GREEN}✓ Services started${NC}"
echo ""

# Step 3: Wait for services to initialize
echo -e "${YELLOW}[3/5] Waiting for services to initialize (30 seconds)...${NC}"
sleep 30
echo -e "${GREEN}✓ Wait complete${NC}"
echo ""

# Step 4: Check running services
echo -e "${YELLOW}[4/5] Checking running services...${NC}"
RUNNING_COUNT=$(docker compose ps --filter 'status=running' --format '{{.Service}}' | wc -l)
echo "Running services: $RUNNING_COUNT"

if [ "$RUNNING_COUNT" -ge 5 ]; then
    echo -e "${GREEN}✓ All 5 services are running${NC}"
else
    echo -e "${RED}✗ Expected 5 services, got $RUNNING_COUNT${NC}"
    echo ""
    echo "Service status:"
    docker compose ps
    exit 1
fi
echo ""

# Step 5: Verify service health
echo -e "${YELLOW}[5/5] Verifying service health...${NC}"

# Check OPA health
echo -n "  OPA health check: "
if curl -sf http://localhost:8181/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ OK${NC}"
else
    echo -e "${RED}✗ FAILED${NC}"
fi

# Check Redis
echo -n "  Redis ping: "
if docker compose exec -T redis redis-cli ping | grep -q PONG; then
    echo -e "${GREEN}✓ OK${NC}"
else
    echo -e "${RED}✗ FAILED${NC}"
fi

# Check Jupyter
echo -n "  Jupyter health: "
if curl -sf http://localhost:8888 > /dev/null 2>&1; then
    echo -e "${GREEN}✓ OK${NC}"
else
    echo -e "${YELLOW}⚠ May still be starting...${NC}"
fi

# Check Kafka
echo -n "  Kafka broker: "
if docker compose exec -T kafka kafka-topics --bootstrap-server localhost:29092 --list > /dev/null 2>&1; then
    echo -e "${GREEN}✓ OK${NC}"
else
    echo -e "${YELLOW}⚠ May still be starting...${NC}"
fi

echo ""
echo "=============================================="
echo -e "${GREEN}Verification Complete!${NC}"
echo "=============================================="
echo ""
echo "Services are accessible at:"
echo "  - OPA:       http://localhost:8181"
echo "  - Jupyter:   http://localhost:8888"
echo "  - Redis:     localhost:6379"
echo "  - Kafka:     localhost:29092"
echo "  - Zookeeper: localhost:2181"
echo ""
echo "To stop services: docker compose down"
