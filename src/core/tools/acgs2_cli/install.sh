#!/bin/bash
# ACGS-2 CLI Tool Installation Script
# Constitutional Hash: cdd01ef066bc6cf2

set -e

echo "🚀 ACGS-2 CLI Tool Installer"
echo "Constitutional Hash: cdd01ef066bc6cf2"
echo

# Check if Python 3.11+ is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.11"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "❌ Python $REQUIRED_VERSION+ is required. Found: $PYTHON_VERSION"
    exit 1
fi

echo "✅ Python $PYTHON_VERSION found"

# Check if pip is available
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is required but not installed."
    exit 1
fi

echo "✅ pip3 found"

# Install the CLI tool
echo
echo "📦 Installing ACGS-2 CLI Tool..."

# First install the SDK if not already installed
if ! python3 -c "import acgs2_sdk" &> /dev/null; then
    echo "📦 Installing ACGS-2 SDK..."
    pip3 install -e ../sdk/python/
fi

# Install the CLI tool
pip3 install -e .

echo
echo "✅ ACGS-2 CLI Tool installed successfully!"
echo
echo "🎯 Quick Start:"
echo "  acgs2_cli --help                    # Show help"
echo "  acgs2_cli health                    # Check system health"
echo "  acgs2_cli playground --interactive  # Start policy playground"
echo
echo "📖 For more information, see README.md"
echo "🔗 Documentation: https://docs.acgs.io/cli"
