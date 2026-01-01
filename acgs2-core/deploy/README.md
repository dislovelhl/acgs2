# Deployment Directory

This directory contains deployment configurations and artifacts for the ACGS-2 core component.

## Contents

### Container Configuration
- `Dockerfile.optimized` - Optimized multi-stage Dockerfile for production builds
- `docker-compose.yml` - Docker Compose configuration for local development and testing

### Deployment Documentation
- `deployment_guide.md` - Comprehensive deployment guide with step-by-step instructions

### Helm Charts
Located in `helm/` subdirectory:
- Kubernetes deployment manifests
- Service configurations
- ConfigMaps and Secrets templates
- Horizontal Pod Autoscalers (HPA)

## Usage

### Local Development
```bash
# Start all services locally
docker-compose -f deploy/docker-compose.yml up -d

# Build optimized production image
docker build -f deploy/Dockerfile.optimized -t acgs2-core:latest .
```

### Production Deployment
```bash
# Deploy using Helm
helm install acgs2-core deploy/helm/acgs2/

# Or apply Kubernetes manifests directly
kubectl apply -f deploy/helm/acgs2/templates/
```

### Deployment Guide
See `deployment_guide.md` for detailed deployment procedures including:
- Prerequisites and system requirements
- Environment-specific configurations
- Troubleshooting common deployment issues
- Rollback procedures

## Deployment Environments

### Development
- Local Docker Compose setup
- Minimal resource requirements
- Full debugging capabilities

### Staging
- Kubernetes deployment with Helm
- Intermediate resource allocation
- Pre-production validation

### Production
- Optimized Docker images
- High availability configuration
- Monitoring and alerting integration

## Constitutional Compliance

**Constitutional Hash**: `cdd01ef066bc6cf2`

All deployment configurations must maintain constitutional governance and include appropriate security measures.

## Maintenance

### Image Updates
- Regularly rebuild Docker images with security patches
- Update base images to latest stable versions
- Optimize image size and build times

### Configuration Management
- Use Helm values files for environment-specific configurations
- Implement ConfigMaps for non-sensitive configuration
- Use Secrets for sensitive data (API keys, certificates)

### Deployment Automation
- Integrate with CI/CD pipelines for automated deployments
- Implement blue-green deployment strategies
- Include health checks and rollback procedures
