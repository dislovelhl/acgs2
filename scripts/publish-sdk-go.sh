#!/bin/bash

# ACGS-2 Go SDK Publishing Script
# Constitutional Hash: cdd01ef066bc6cf2

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SDK_DIR="$PROJECT_ROOT/acgs2-core/sdk/go"

echo "=========================================="
echo "ACGS-2 Go SDK Publishing Script"
echo "=========================================="

# Validate inputs
if [ -z "$1" ]; then
    echo "Usage: $0 <version> [tag-prefix]"
    echo "Example: $0 v1.0.0 sdk/go"
    exit 1
fi

VERSION="$1"
TAG_PREFIX="${2:-sdk/go}"

echo "Version: $VERSION"
echo "Tag Prefix: $TAG_PREFIX"

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "❌ Not in a git repository"
    exit 1
fi

# Check for uncommitted changes
if ! git diff --quiet || ! git diff --staged --quiet; then
    echo "❌ There are uncommitted changes. Please commit or stash them first."
    exit 1
fi

cd "$PROJECT_ROOT"

# Create and push tag
TAG_NAME="$TAG_PREFIX/$VERSION"
echo "Creating tag: $TAG_NAME"

if git tag -l | grep -q "^$TAG_NAME$"; then
    echo "❌ Tag $TAG_NAME already exists"
    exit 1
fi

git tag -a "$TAG_NAME" -m "Release $TAG_NAME"
git push origin "$TAG_NAME"

echo "✅ Tag $TAG_NAME created and pushed"

# Update go.mod for publishing (temporarily)
echo "Updating go.mod for publishing..."
cd "$SDK_DIR"

# Backup original go.mod
cp go.mod go.mod.backup

# Update to the correct module path for publishing
cat > go.mod << EOF
module github.com/acgs2/sdk/go

go 1.21
EOF

# Add dependencies that are actually used
go mod tidy

echo "✅ Go module updated for publishing"

# Create go.sum if it doesn't exist
if [ ! -f go.sum ]; then
    go mod download
fi

# Validate the module can be built
echo "Validating Go SDK..."
go build ./...

if [ -d "examples" ]; then
    echo "Validating examples..."
    for example in examples/*.go; do
        echo "Building example: $example"
        go build -o /dev/null "$example"
    done
fi

echo "✅ Go SDK validation complete"

# Restore original go.mod for local development
mv go.mod.backup go.mod

echo "✅ Restored local go.mod"

# Instructions for Go module proxy
echo ""
echo "=========================================="
echo "PUBLISHING COMPLETE!"
echo "=========================================="
echo ""
echo "The Go SDK has been tagged and pushed to GitHub."
echo ""
echo "Next steps:"
echo "1. The module will be automatically available via Go module proxy"
echo "2. Users can install with: go get github.com/acgs2/sdk/go@$VERSION"
echo "3. Verify: https://pkg.go.dev/github.com/acgs2/sdk/go@$VERSION"
echo ""
echo "Note: Go modules are distributed via Git tags and the Go module proxy."
echo "No additional publishing step is required."
