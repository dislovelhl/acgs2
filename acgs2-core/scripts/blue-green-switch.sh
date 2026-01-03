#!/bin/bash

# Blue-Green Traffic Switch Script for ACGS-2
# This script switches traffic from blue to green environment

set -e

NAMESPACE="acgs2"
GREEN_INGRESS="adaptive-governance-green-ingress"
PERCENTAGE=${1:-100}

echo "Switching traffic to green environment..."
echo "Namespace: $NAMESPACE"
echo "Traffic Percentage: $PERCENTAGE%"

# Update the canary weight annotation
kubectl annotate ingress $GREEN_INGRESS nginx.ingress.kubernetes.io/canary-weight="$PERCENTAGE" -n $NAMESPACE --overwrite

echo "Traffic switched to $PERCENTAGE% green environment"

if [ "$PERCENTAGE" -eq 100 ]; then
    echo "Full traffic switch completed. Green environment is now live."
    echo "Monitor the system for 15-30 minutes before scaling down blue environment."
fi
