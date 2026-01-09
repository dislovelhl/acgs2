#!/bin/bash
# export_clean_source.sh
# Generates a clean source archive containing ONLY files tracked by Git.
# This prevents sensitive untracked files (like .env) or transient build artifacts
# from being accidentally included in shared or distributed ZIPs.

set -e

# Repository Root
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUTPUT_DIR="${REPO_ROOT}/releases"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
OUTPUT_FILE="${OUTPUT_DIR}/acgs2_clean_source_${TIMESTAMP}.zip"

mkdir -p "${OUTPUT_DIR}"

echo ">>> Exporting clean source to: ${OUTPUT_FILE}"

# Use git archive to capture only tracked files
# -o specifies the output file
# HEAD refers to the current commit/branch
# The format is inferred from the extension (.zip or .tar.gz)
(cd "${REPO_ROOT}" && git archive -o "${OUTPUT_FILE}" HEAD)

echo ">>> Clean export complete."
echo ">>> Verifying export size and content..."
du -sh "${OUTPUT_FILE}"

# Optional: verify no .env files in the zip
if command -v unzip > /dev/null; then
    if unzip -l "${OUTPUT_FILE}" | grep -E "\.env$|/\.env$" > /dev/null; then
        echo "!!! WARNING: .env files found in the archive! This script only exports tracked files."
        echo "!!! If a .env file is tracked, it WILL be included. Run 'git ls-files .env' to check."
    else
        echo ">>> Success: No .env files found in the clean archive."
    fi
fi
