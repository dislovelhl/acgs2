#!/bin/bash
# Adaptive Learning Engine - Development Environment Activation
# Constitutional Hash: cdd01ef066bc6cf2

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Adaptive Learning Engine - Development Environment${NC}"
echo "Constitutional Hash: cdd01ef066bc6cf2"
echo ""

# Activate virtual environment
source .venv/bin/activate

# Set Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Display environment info
echo -e "${GREEN}✓ Virtual environment activated${NC}"
echo -e "${GREEN}✓ Python version: $(python --version)${NC}"
echo -e "${GREEN}✓ PYTHONPATH configured${NC}"
echo ""
echo "Quick commands:"
echo "  pytest              - Run all tests"
echo "  pytest -v           - Run tests with verbose output"
echo "  python src/main.py  - Start development server"
echo "  pip list            - Show installed packages"
echo ""
