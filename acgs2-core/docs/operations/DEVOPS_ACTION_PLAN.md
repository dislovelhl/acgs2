# ACGS-2 DevOps Action Plan

**Constitutional Hash:** `cdd01ef066bc6cf2`
**Created:** 2025-12-25
**Target Completion:** 2026-03-25 (Q1 2026)

---

## Phase 1: Critical Security Hardening (Week 1-2)

### Task 1.1: Docker Security Standardization
**Owner:** DevOps Team
**Timeline:** Week 1 (2025-12-25 to 2025-12-31)
**Priority:** CRITICAL

#### Task 1.1.1: Create Base Dockerfile Template
```dockerfile
# Standardized ACGS-2 Python Service Dockerfile
FROM python:3.13-slim as builder

WORKDIR /build
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt

FROM python:3.13-slim

WORKDIR /app

# Security: Create non-root user
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app

# Install runtime dependencies
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages

# Copy application code
COPY --chown=app:app . .

# Security: Drop privileges
USER app

# Health check (customize port as needed)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health/ready || exit 1

# Expose port
EXPOSE ${PORT:-8000}

# Run application
CMD ["python", "-m", "app.main"]
```

**Services to Update:**
- [ ] `enhanced_agent_bus/deliberation_layer/Dockerfile`
- [ ] `services/core/constraint_generation_system/Dockerfile`
- [ ] `services/integration/search_platform/Dockerfile`
- [ ] `enhanced_agent_bus/rust/Dockerfile` (after Python stage)

#### Task 1.1.2: Add Security Scanning to CI/CD
```yaml
# Add to .github/workflows/security-scan.yml

- name: Scan Docker Images with Trivy
  uses: aquasecurity/trivy-action@master
  with:
    scan-type: 'image'
    image-ref: ${{ env.REGISTRY }}/${{ env.IMAGE }}:${{ env.TAG }}
    format: 'sarif'
    output: 'trivy-image-results.sarif'
    severity: 'HIGH,CRITICAL'
    exit-code: '1'

- name: Upload Trivy Results
  uses: github/codeql-action/upload-sarif@v2
  with:
    sarif_file: 'trivy-image-results.sarif'
```

**Acceptance Criteria:**
- [ ] All 6 Dockerfiles updated with health checks
- [ ] All services have non-root user (UID 1000)
- [ ] Security scanning integrated in CI/CD
- [ ] No vulnerabilities in critical/high severity
- [ ] Image builds complete <5 minutes

---

### Task 1.2: Terraform State Backend Configuration
**Owner:** Infrastructure Team
**Timeline:** Week 1-2
**Priority:** CRITICAL

#### Task 1.2.1: Uncomment and Document Backend

```hcl
# deploy/terraform/aws/main.tf

terraform {
  backend "s3" {
    bucket         = "acgs2-terraform-state-${AWS_ACCOUNT_ID}"
    key            = "aws/terraform.tfstate"
    region         = "us-west-2"
    encrypt        = true
    dynamodb_table = "acgs2-terraform-locks"
  }
}

# Add DynamoDB table for state locking
resource "aws_dynamodb_table" "terraform_locks" {
  name           = "acgs2-terraform-locks"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  server_side_encryption_specification {
    enabled     = true
    kms_key_arn = module.kms.key_arn
  }

  point_in_time_recovery_specification {
    enabled = true
  }

  tags = local.common_tags
}
```

**Setup Steps:**
1. Create S3 bucket: `acgs2-terraform-state-${AWS_ACCOUNT_ID}`
2. Enable versioning on S3 bucket
3. Enable default encryption (KMS)
4. Block public access
5. Create DynamoDB table
6. Update CI/CD with credentials

**Acceptance Criteria:**
- [ ] S3 bucket created and encrypted
- [ ] DynamoDB lock table created
- [ ] State locked during apply
- [ ] State versioning enabled
- [ ] Backup strategy documented

---

### Task 1.3: SLSA Provenance Generation
**Owner:** Security Team
**Timeline:** Week 2
**Priority:** HIGH

#### Task 1.3.1: Add SLSA Generator Workflow

Create `.github/workflows/slsa-release.yml`:

```yaml
name: SLSA Release

on:
  push:
    branches: [main]
    tags: ['v*']
  workflow_dispatch:

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      image-digest: ${{ steps.build.outputs.digest }}
      image-name: ${{ steps.meta.outputs.tags }}
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=semver,pattern={{version}}
            type=sha

      - name: Build and push
        id: build
        uses: docker/build-push-action@v5
        with:
          context: enhanced_agent_bus
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          sbom: true
          provenance: mode=max
          cache-from: type=gha
          cache-to: type=gha,mode=max

  provenance:
    needs: build
    permissions:
      contents: read
      packages: write
      id-token: write
    uses: slsa-framework/slsa-github-generator/.github/workflows/generator_container_slsa3.yml@v1.10.0
    with:
      image: ${{ needs.build.outputs.image-name }}
      digest: ${{ needs.build.outputs.image-digest }}
      registry-username: ${{ github.actor }}
    secrets:
      registry-password: ${{ secrets.GITHUB_TOKEN }}

  verify:
    needs: provenance
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write
    steps:
      - name: Verify image signature
        uses: slsa-framework/slsa-verifier/actions/docker-verify@v2.5.0
        with:
          image-download-outcome: success
          image: ${{ needs.build.outputs.image-name }}
          image-digest: ${{ needs.build.outputs.image-digest }}
```

**Acceptance Criteria:**
- [ ] SLSA provenance generated on build
- [ ] Provenance uploaded to registry
- [ ] Verification workflow passes
- [ ] Image digest matches provenance
- [ ] Documentation updated

---

## Phase 2: GitOps & Deployment Automation (Week 3-4)

### Task 2.1: ArgoCD Integration
**Owner:** DevOps Team
**Timeline:** Week 3-4
**Priority:** HIGH

#### Task 2.1.1: Install ArgoCD

```bash
# Add to scripts/install-argocd.sh
#!/bin/bash

set -e

NAMESPACE="argocd"
VERSION="2.10.0"

# Create namespace
kubectl create namespace $NAMESPACE || true

# Install ArgoCD
helm repo add argocd https://argoproj.github.io/argo-helm
helm repo update

helm install argocd argocd/argo-cd \
  --namespace $NAMESPACE \
  --version $VERSION \
  --values - <<EOF
configs:
  secret:
    argocdServerAdminPassword: $(bcrypt -C 10 $(openssl rand -base64 32))
  cm:
    url: https://argocd.acgs.example.com
    dex.config: |
      connectors:
        - type: oidc
          id: oidc
          name: OIDC Provider
          config:
            issuer: https://auth.acgs.example.com
            clientID: $ARGOCD_CLIENT_ID
            clientSecret: $ARGOCD_CLIENT_SECRET

dex:
  enabled: true

controller:
  replicas: 3
  resources:
    requests:
      cpu: 500m
      memory: 512Mi
    limits:
      cpu: 2000m
      memory: 2Gi

server:
  replicas: 2
  ingress:
    enabled: true
    ingressClassName: nginx
    hosts:
      - argocd.acgs.example.com
    tls:
      - secretName: argocd-tls
        hosts:
          - argocd.acgs.example.com

repoServer:
  replicas: 2

redis:
  enabled: true
EOF

# Wait for deployment
kubectl rollout status deployment/argocd-server -n $NAMESPACE --timeout=5m
echo "ArgoCD installed successfully"
```

#### Task 2.1.2: Create ArgoCD Applications

```yaml
# deploy/argocd/acgs2-app.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: acgs2
  namespace: argocd
spec:
  project: acgs2

  source:
    repoURL: https://github.com/acgs/acgs2
    targetRevision: main
    path: deploy/helm/acgs2
    helm:
      values: |
        global:
          constitutionalHash: "cdd01ef066bc6cf2"
          environment: production

        constitutionalService:
          replicaCount: 3
          resources:
            requests:
              cpu: 500m
              memory: 512Mi
            limits:
              cpu: 2000m
              memory: 2Gi

  destination:
    server: https://kubernetes.default.svc
    namespace: acgs2

  syncPolicy:
    automated:
      prune: true
      selfHeal: true
      allowEmpty: false
    syncOptions:
      - CreateNamespace=true
      - PrunePropagationPolicy=foreground
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m

  # Health assessment
  ignoreDifferences:
    - group: apps
      kind: Deployment
      jsonPointers:
        - /spec/replicas

  # Post-sync
  hooks:
    postSync:
      - goTemplate:
          template: |
            apiVersion: batch/v1
            kind: Job
            metadata:
              name: acgs2-post-sync-{{ .Now | date "20060102150405" }}
            spec:
              template:
                spec:
                  serviceAccountName: acgs2
                  containers:
                  - name: post-sync
                    image: acgs/acgs2-tools:latest
                    command:
                    - /bin/sh
                    - -c
                    - |
                      echo "Running post-sync checks..."
                      kubectl wait --for=condition=available --timeout=300s deployment/acgs2-api -n acgs2
                      echo "Post-sync completed"
                  restartPolicy: Never
              backoffLimit: 3
```

**Acceptance Criteria:**
- [ ] ArgoCD installed and accessible
- [ ] OIDC provider configured
- [ ] Application syncs automatically
- [ ] Drift detection working
- [ ] Rollback tested and working

---

### Task 2.2: Argo Rollouts for Canary Deployments
**Owner:** DevOps Team
**Timeline:** Week 4
**Priority:** HIGH

#### Task 2.2.1: Install Argo Rollouts

```yaml
# deploy/helm/acgs2-rollouts/Chart.yaml
apiVersion: v2
name: acgs2-rollouts
description: Argo Rollouts configuration for ACGS-2
type: application
version: 1.0.0

# deploy/helm/acgs2-rollouts/templates/rollout.yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
metadata:
  name: {{ .Values.name }}-rollout
spec:
  replicas: {{ .Values.replicaCount }}

  selector:
    matchLabels:
      app: {{ .Values.name }}

  template:
    metadata:
      labels:
        app: {{ .Values.name }}
      annotations:
        constitutional-hash: "cdd01ef066bc6cf2"
    spec:
      containers:
      - name: {{ .Values.name }}
        image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
        ports:
        - containerPort: {{ .Values.port }}
        resources:
          requests:
            cpu: {{ .Values.resources.requests.cpu }}
            memory: {{ .Values.resources.requests.memory }}
          limits:
            cpu: {{ .Values.resources.limits.cpu }}
            memory: {{ .Values.resources.limits.memory }}

  strategy:
    canary:
      steps:
      - setWeight: 10
      - pause:
          duration: 5m
      - setWeight: 25
      - pause:
          duration: 5m
      - setWeight: 50
      - pause:
          duration: 5m
      - setWeight: 75
      - pause:
          duration: 5m

      canaryService: {{ .Values.name }}-canary
      stableService: {{ .Values.name }}-stable

      analysis:
        interval: 1m
        threshold: 5
        metrics:
        - name: p99-latency
          interval: 1m
          query: |
            histogram_quantile(0.99,
              rate(http_request_duration_seconds_bucket[1m])
            )
          thresholdRange:
            max: 5  # 5ms

        - name: error-rate
          interval: 1m
          query: |
            rate(http_requests_total{status=~"5.."}[1m]) /
            rate(http_requests_total[1m])
          thresholdRange:
            max: 0.01  # 1%

        args:
          prometheus-address: http://prometheus:9090
```

**Acceptance Criteria:**
- [ ] Argo Rollouts installed
- [ ] Canary strategy configured
- [ ] Metrics analysis working
- [ ] Automatic rollback on failure
- [ ] Traffic shifting validated

---

## Phase 3: Observability Enhancement (Week 5-6)

### Task 3.1: Distributed Tracing with OpenTelemetry
**Owner:** Platform Team
**Timeline:** Week 5
**Priority:** HIGH

#### Task 3.1.1: Deploy OTel Collector

```yaml
# deploy/helm/otel-collector/values.yaml
mode: daemonset

presets:
  kubernetesAttributes:
    enabled: true
  kubeletMetrics:
    enabled: true

config:
  receivers:
    otlp:
      protocols:
        grpc:
          endpoint: 0.0.0.0:4317
        http:
          endpoint: 0.0.0.0:4318

    prometheus:
      config:
        scrape_configs:
          - job_name: kubernetes-pods
            kubernetes_sd_configs:
              - role: pod

  exporters:
    jaeger:
      endpoint: jaeger-collector.observability:14250

    prometheus:
      endpoint: "0.0.0.0:8888"

  processors:
    batch:
      send_batch_size: 1024
      timeout: 10s

    memory_limiter:
      check_interval: 1s
      limit_mib: 1024

  service:
    pipelines:
      traces:
        receivers: [otlp]
        processors: [memory_limiter, batch]
        exporters: [jaeger]

      metrics:
        receivers: [otlp, prometheus]
        processors: [memory_limiter, batch]
        exporters: [prometheus]

podAnnotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "8888"
```

**Acceptance Criteria:**
- [ ] OTel Collector deployed
- [ ] Jaeger backend operational
- [ ] Traces being collected
- [ ] Dashboard showing traces
- [ ] Error tracing working

---

### Task 3.2: Advanced Monitoring with Alerting
**Owner:** Platform Team
**Timeline:** Week 5-6
**Priority:** HIGH

#### Task 3.2.1: Create PrometheusRules

```yaml
# deploy/helm/acgs2/templates/prometheus-rules.yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: acgs2-rules
spec:
  groups:
    - name: acgs2.rules
      interval: 30s
      rules:
        # Latency Alerts
        - alert: HighP99Latency
          expr: |
            histogram_quantile(0.99,
              rate(http_request_duration_seconds_bucket[5m])
            ) > 0.005
          for: 5m
          annotations:
            summary: "P99 latency exceeds 5ms"
            runbook_url: "https://wiki.acgs.io/alerts/high-latency"

        # Throughput Alerts
        - alert: LowThroughput
          expr: |
            rate(http_requests_total[5m]) < 100
          for: 5m
          annotations:
            summary: "Throughput below 100 RPS"

        # Error Rate Alerts
        - alert: HighErrorRate
          expr: |
            rate(http_requests_total{status=~"5.."}[5m]) /
            rate(http_requests_total[5m]) > 0.01
          for: 5m
          annotations:
            summary: "Error rate exceeds 1%"

        # Constitutional Compliance
        - alert: ConstitutionalViolation
          expr: |
            increase(constitutional_violations_total[5m]) > 0
          for: 1m
          annotations:
            summary: "Constitutional compliance violation detected"
            severity: "critical"

        # Resource Utilization
        - alert: HighMemoryUsage
          expr: |
            container_memory_usage_bytes{pod=~"acgs2.*"} /
            container_spec_memory_limit_bytes > 0.9
          for: 5m
          annotations:
            summary: "Memory usage above 90%"

        - alert: HighCPUUsage
          expr: |
            rate(container_cpu_usage_seconds_total{pod=~"acgs2.*"}[5m]) > 0.8
          for: 5m
          annotations:
            summary: "CPU usage above 80%"

        # Cache Performance
        - alert: LowCacheHitRate
          expr: |
            rate(cache_hits_total[5m]) /
            (rate(cache_hits_total[5m]) + rate(cache_misses_total[5m])) < 0.85
          for: 10m
          annotations:
            summary: "Cache hit rate below 85%"
```

**Acceptance Criteria:**
- [ ] All alerts configured
- [ ] Alert routing working
- [ ] Slack notifications sent
- [ ] PagerDuty escalation working
- [ ] Runbook links present

---

## Phase 4: Advanced Security (Week 7-8)

### Task 4.1: Container Image Signing with Cosign
**Owner:** Security Team
**Timeline:** Week 7
**Priority:** MEDIUM

#### Task 4.1.1: Add Cosign Integration

```yaml
# .github/workflows/image-signing.yml
name: Sign Container Images

on:
  push:
    branches: [main]
    paths:
      - 'enhanced_agent_bus/**'
      - '.github/workflows/image-signing.yml'

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  build-and-sign:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
      id-token: write

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push image
        id: build
        uses: docker/build-push-action@v5
        with:
          context: enhanced_agent_bus
          push: true
          tags: |
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:latest
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Install Cosign
        uses: sigstore/cosign-installer@v3
        with:
          cosign-release: 'v2.2.0'

      - name: Sign image with Cosign (Keyless)
        env:
          COSIGN_EXPERIMENTAL: 1
        run: |
          cosign sign --yes \
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}@${{ steps.build.outputs.digest }}

      - name: Verify image signature
        env:
          COSIGN_EXPERIMENTAL: 1
        run: |
          cosign verify \
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}@${{ steps.build.outputs.digest }}
```

**Acceptance Criteria:**
- [ ] Images signed with Cosign
- [ ] Signature verification working
- [ ] Keyless signing configured
- [ ] Registry policy enforced
- [ ] Documentation updated

---

## Phase 5: Network & Policy as Code (Week 9-10)

### Task 5.1: Kubernetes Network Policies
**Owner:** Platform Team
**Timeline:** Week 9
**Priority:** MEDIUM

#### Task 5.1.1: Create Network Policies

```yaml
# deploy/helm/acgs2/templates/network-policies.yaml
{{- if .Values.global.security.networkPolicy.enabled }}
---
# Allow all traffic within acgs2 namespace
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: {{ include "acgs2.fullname" . }}-allow-internal
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: {{ .Release.Namespace }}
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              name: {{ .Release.Namespace }}
    # Allow DNS
    - to:
        - podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - protocol: UDP
          port: 53
    # Allow external APIs
    - to:
        - namespaceSelector:
            matchLabels:
              name: kube-system

---
# Deny all ingress by default
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: {{ include "acgs2.fullname" . }}-deny-all-ingress
spec:
  podSelector: {}
  policyTypes:
    - Ingress

---
# Allow ingress from API Gateway
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: {{ include "acgs2.fullname" . }}-allow-api-gateway
spec:
  podSelector:
    matchLabels:
      app: acgs2-service
  policyTypes:
    - Ingress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: api-gateway
      ports:
        - protocol: TCP
          port: 8000
{{- end }}
```

**Acceptance Criteria:**
- [ ] Network policies deployed
- [ ] Pod-to-pod communication verified
- [ ] External access restricted
- [ ] DNS resolution working
- [ ] Tests passing

---

### Task 5.2: OPA Policy as Code
**Owner:** Security Team
**Timeline:** Week 9-10
**Priority:** MEDIUM

#### Task 5.2.1: Create Rego Policies

```rego
# policies/rego/kubernetes.rego
package kubernetes.admission

import future.keywords

# Deny containers without security context
deny[msg] {
    input.request.kind.kind == "Pod"
    not input.request.object.spec.securityContext.runAsNonRoot
    msg := "Pod must run as non-root"
}

# Require resource limits
deny[msg] {
    input.request.kind.kind == "Deployment"
    container := input.request.object.spec.template.spec.containers[_]
    not container.resources.limits.memory
    msg := sprintf("Container %v must have memory limit", [container.name])
}

# Require constitutional hash
deny[msg] {
    input.request.kind.kind in ["Pod", "Deployment"]
    not contains_constitutional_hash(input.request.object)
    msg := "Resource missing constitutional hash annotation"
}

contains_constitutional_hash(obj) {
    obj.metadata.annotations["constitutional-hash"] == "cdd01ef066bc6cf2"
}

# Allow privileged containers only in system namespace
deny[msg] {
    input.request.kind.kind == "Pod"
    input.request.namespace != "kube-system"
    container := input.request.object.spec.containers[_]
    container.securityContext.privileged
    msg := "Privileged containers not allowed outside system namespace"
}
```

**Acceptance Criteria:**
- [ ] Policies deployed to OPA
- [ ] Policies enforced in cluster
- [ ] Violations blocked
- [ ] Dry-run testing working
- [ ] Documentation updated

---

## Phase 6: Disaster Recovery & Cost Optimization (Week 11-12)

### Task 6.1: Cross-Region Disaster Recovery
**Owner:** Infrastructure Team
**Timeline:** Week 11
**Priority:** MEDIUM

#### Task 6.1.1: Add Cross-Region Terraform

```hcl
# deploy/terraform/aws/modules/dr/main.tf
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

variable "primary_region" {
  type = string
}

variable "dr_region" {
  type = string
}

variable "rds_snapshot_id" {
  type = string
}

# DR RDS Restore in secondary region
resource "aws_db_instance" "dr_replica" {
  provider = aws.dr

  identifier = "acgs2-dr-db"

  snapshot_identifier = var.rds_snapshot_id
  instance_class      = "db.r5.xlarge"

  skip_final_snapshot = false
  final_snapshot_identifier = "acgs2-dr-final-snapshot"

  enabled_cloudwatch_logs_exports = ["postgresql"]

  tags = {
    Name = "ACGS-2 DR Database"
  }
}

# Route53 Failover
resource "aws_route53_health_check" "primary" {
  ip_address        = var.primary_endpoint
  port              = 443
  type              = "HTTPS"
  failure_threshold = 3
  request_interval  = 30

  tags = {
    Name = "ACGS-2 Primary Health"
  }
}

resource "aws_route53_record" "failover_primary" {
  zone_id = var.route53_zone_id
  name    = "api.acgs.example.com"
  type    = "A"

  failover_routing_policy {
    type = "PRIMARY"
  }

  health_check_id = aws_route53_health_check.primary.id
  set_identifier  = "Primary"
  alias {
    name    = var.primary_lb_dns
    zone_id = var.primary_zone_id
    evaluate_target_health = true
  }
}

resource "aws_route53_record" "failover_secondary" {
  zone_id = var.route53_zone_id
  name    = "api.acgs.example.com"
  type    = "A"

  failover_routing_policy {
    type = "SECONDARY"
  }

  set_identifier = "Secondary"
  alias {
    name    = var.dr_lb_dns
    zone_id = var.dr_zone_id
    evaluate_target_health = true
  }
}
```

**Acceptance Criteria:**
- [ ] DR infrastructure in secondary region
- [ ] RDS replication working
- [ ] Route53 failover configured
- [ ] Failover tested and working
- [ ] RTO/RPO documented

---

## Success Criteria & Metrics

### Phase Completion Checklist

- [ ] Phase 1: All Dockerfiles hardened, SLSA enabled
- [ ] Phase 2: ArgoCD deployed, canary deployments working
- [ ] Phase 3: Distributed tracing operational, all alerts configured
- [ ] Phase 4: Images signed and verified, policy enforcement active
- [ ] Phase 5: Network policies deployed, OPA policies enforced
- [ ] Phase 6: DR tested, cost baselines established

### Performance Metrics (Track Throughout)

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| Build time | ~10 min | <5 min | Improve |
| Deploy time | ~15 min | <5 min | Improve |
| MTTR | Unknown | <15 min | Track |
| Security scan time | ~2 min | <1 min | Improve |
| Test execution | ~5 min | <3 min | Improve |

---

## Resource Requirements

| Phase | Team | Effort | Hardware |
|-------|------|--------|----------|
| 1 | DevOps (2) + Security (1) | 40 hours | NA |
| 2 | DevOps (2) + Platform (1) | 60 hours | NA |
| 3 | Platform (2) | 50 hours | NA |
| 4 | Security (2) | 40 hours | NA |
| 5 | Platform (2) | 40 hours | NA |
| 6 | Infrastructure (2) | 50 hours | DR environment |

**Total Effort:** ~280 hours (7 weeks × 40-hour weeks)

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Production downtime during deployment | High | Use blue-green in phase 2 |
| Security scanning bottleneck | Medium | Parallelize scanning in phase 1 |
| OPA policy too restrictive | Medium | Start with audit mode in phase 5 |
| Cross-region failover cost | Medium | Monitor and optimize in phase 6 |

---

## Sign-Off

**Review Status:** Ready for Implementation
**Constitutional Hash:** `cdd01ef066bc6cf2`
**Next Review:** Post-Phase 1 (2026-01-07)

---

**Document Version:** 1.0.0
**Last Updated:** 2025-12-25
