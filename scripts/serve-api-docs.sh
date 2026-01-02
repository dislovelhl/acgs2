#!/bin/bash
# Serve ACGS-2 API Documentation locally

echo "📚 Serving ACGS-2 API Documentation..."

# Check if Python is available
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ Python is not installed. Please install Python 3."
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "docs/api/index.html" ]; then
    echo "❌ API documentation not found. Please run this script from the ACGS-2 root directory."
    exit 1
fi

# Start HTTP server
echo "🌐 Starting documentation server on http://localhost:8001"
echo "📖 Open your browser to view the API documentation"
echo "🛑 Press Ctrl+C to stop the server"
echo ""

cd docs/api && $PYTHON_CMD -m http.server 8001
