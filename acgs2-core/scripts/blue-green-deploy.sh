#!/bin/bash

# Blue-Green Deployment Script for ACGS-2
# This script deploys a new version to the green environment

set -e

NAMESPACE="acgs2"
GREEN_DEPLOYMENT="adaptive-governance-green"
GREEN_SERVICE="adaptive-governance-green-service"
NEW_IMAGE_TAG=${1:-"latest"}

echo "Starting blue-green deployment..."
echo "Namespace: $NAMESPACE"
echo "Green Deployment: $GREEN_DEPLOYMENT"
echo "New Image Tag: $NEW_IMAGE_TAG"

# Update the green deployment with new image
echo "Updating green deployment with new image..."
kubectl set image deployment/$GREEN_DEPLOYMENT adaptive-governance=acgs2/adaptive-governance:$NEW_IMAGE_TAG -n $NAMESPACE

# Scale up green deployment
echo "Scaling up green deployment to 3 replicas..."
kubectl scale deployment $GREEN_DEPLOYMENT --replicas=3 -n $NAMESPACE

# Wait for rollout to complete
echo "Waiting for green deployment rollout to complete..."
kubectl rollout status deployment/$GREEN_DEPLOYMENT -n $NAMESPACE

# Run health checks
echo "Running health checks on green environment..."
./scripts/health-check.sh $GREEN_SERVICE

echo "Green environment deployment completed successfully!"
echo "You can now switch traffic using the switch script."
