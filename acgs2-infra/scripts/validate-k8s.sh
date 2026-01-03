#!/bin/bash
set -euo pipefail

echo "Validating ACGS-2 K8s manifests with kubeval..."

cd "$(dirname "$0")/../"

# Render helm templates
helm template acgs2 deploy/helm/acgs2 --values deploy/helm/acgs2/values.yaml --namespace acgs2 | kubeval --quiet --ignore-missing-schemas

# Or validate templates directly
# kubeval --directory deploy/helm/acgs2/templates --ignore-missing-schemas --quiet

echo "✅ K8s validation passed"
