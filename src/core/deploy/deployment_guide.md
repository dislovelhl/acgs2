# ACGS-2 Deployment Guide (v2.3.0)

> **Constitutional Hash**: `cdd01ef066bc6cf2`  
> **Version**: 2.3.0 (Phase 3.6 Complete)  
> **Perf Targets**: P99 <5ms, 99.8% tests, 100% cov  
> **Last Updated**: 2025-12-31

## Docker Compose (Local/Dev)

Updated v3.9+ with limits/health/TLS.

```yaml
version: '3.9'
services:
  rust-message-bus:
    build:
      context: ./enhanced_agent_bus/rust
    ports:
      - "8080:8080"
    env_file:
      - .env
    user: "1000:1000"
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:8080/health || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
    networks:
      - acgs2-net
  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
  opa:
    image: openpolicyagent/opa:latest
    ports:
      - "8181:8181"
    command: run --server /policies
    volumes:
      - ./policies/rego:/policies
```

**Quickstart**:
```bash
docker compose up -d
docker compose logs -f rust-message-bus
```

## Helm (Production)

RBAC/networkPolicy enabled.

```bash
helm repo add acgs2 https://charts.acgs2.io
helm install acgs2 ./deploy/helm/acgs2 -n acgs2 --create-namespace \
  --set image.tag=2.3.0 \
  --set resources.requests.cpu=500m \
  --set resources.requests.memory=1Gi \
  --set rbac.enabled=true \
  --set networkPolicy.enabled=true
```

**Values** [`deploy/helm/acgs2/values.yaml`](deploy/helm/acgs2/values.yaml):
- TLS: cert-manager internal certs
- Limits: CPU 500m, Mem 1Gi
- Healthchecks: readiness/liveness probes

## Verification

```bash
kubectl get pods -n acgs2
curl http://localhost:8080/health  # docker
kubectl port-forward svc/rust-message-bus 8080:8080 -n acgs2  # k8s
```

See [C4 Container](C4-Documentation/c4-container-acgs2.md).
