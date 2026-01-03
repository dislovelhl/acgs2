#!/bin/bash

# Blue-Green Rollback Script for ACGS-2
# This script rolls back traffic to the blue environment

set -e

NAMESPACE="acgs2"
GREEN_INGRESS="adaptive-governance-green-ingress"
BLUE_DEPLOYMENT="adaptive-governance-blue"
GREEN_DEPLOYMENT="adaptive-governance-green"

echo "Starting rollback to blue environment..."
echo "Namespace: $NAMESPACE"

# Immediately switch all traffic back to blue
echo "Running health check on blue environment before rollback..."
./scripts/health-check.sh

echo "Switching all traffic back to blue environment..."
kubectl annotate ingress $GREEN_INGRESS nginx.ingress.kubernetes.io/canary-weight="0" -n $NAMESPACE --overwrite

# Wait a moment for traffic to drain
echo "Waiting for traffic to drain from green environment..."
sleep 30

# Scale down green deployment to save resources
echo "Scaling down green deployment..."
kubectl scale deployment $GREEN_DEPLOYMENT --replicas=0 -n $NAMESPACE

# Verify blue deployment is healthy
echo "Verifying blue deployment health..."
kubectl rollout status deployment/$BLUE_DEPLOYMENT -n $NAMESPACE

echo "Rollback completed successfully!"
echo "All traffic is now routed to the blue environment."
echo "Green environment has been scaled down."
