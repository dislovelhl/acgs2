# ACGS2 Observability Enhancements for Production Readiness

## Overview

This document details the deployment of custom Prometheus alerting rules and Grafana dashboards for tracking:

- MACI role violations (`maci_deny_count`)
- TLS handshake failures (`ssl_errors_total`)
- RBAC denials (`rbac_violations_total`)
- Custom alerts for `error_rate > 0.01` and `violation_rate > 0.001`
- SLO dashboard for 99.99% uptime (4h error budget/month)

Compatible with existing Helm/IaC and TLS ports (Alertmanager bootstrap:9093, Redis rediss:6380, OPA https:8181).

## Key PromQL Queries

- MACI deny rate: `rate(maci_deny_count[5m])`
- TLS error rate: `rate(ssl_errors_total[5m])`
- RBAC violation rate: `rate(rbac_violations_total[5m])`
- Error rate: `rate(http_requests_total{status=~"4..|5.."}[5m]) / rate(http_requests_total[5m])`
- Violation rate: `rate((maci_deny_count + ssl_errors_total + rbac_violations_total)[5m])`
- SLO availability: `1 - error_rate`
- Error budget burn rate (5m): `error_rate / 0.0001`
- Error budget remaining (30d): `0.0001 * 2592000 - sum_over_time(error_rate[30d]) * 2592000` (seconds)

## Deployment Steps

### 1. Prometheus Alerting Rules

**Option A: K8s Prometheus Operator (PrometheusRule CRD)**

```bash
kubectl apply -f monitoring/prometheus-rules.yaml -n monitoring
```

**Option B: Standalone Prometheus (plain rules)**

```bash
# Copy to Prometheus pod
kubectl cp monitoring/alerts/acgs2-security-rules.yaml monitoring/prometheus-server:/etc/prometheus/rules/
kubectl exec -n monitoring prometheus-server -- prometheus --config.file=/etc/prometheus/prometheus.yml --storage.tsdb.path=/prometheus --web.console.libraries=/etc/prometheus/console_libraries --web.console.templates=/etc/prometheus/consoles --web.enable-lifecycle --storage.tsdb.retention.time=200h --web.enable-admin-api reload
```

### 2. Grafana Dashboard Import

1. Login to Grafana (`http://localhost:3000`, admin/admin)
2. Dashboards > Import
3. Upload `monitoring/grafana-dashboards-acgs2-security-slo.json`
4. Select Prometheus datasource
5. Import

**Provisioning (recommended)**

Add to Grafana provisioning/dashboards:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-dashboards
data:
  acgs2-security-slo.json: | 
    # paste json content
```

### 3. Helm Values Update for TLS/mTLS (if not already)

In `helm/values.yaml`:

```yaml
alertmanager:
  service:
    ports:
      bootstrap: 9093
redis:
  auth:
    enabled: true
  tls:
    enabled: true
    port: 6380
opa:
  service:
    ports:
      https: 8181
```

```bash
helm upgrade acgs2 ./helm/acgs2 -f values.yaml --namespace acgs2 --create-namespace
```

### 4. Validation

```bash
# Kubeval for K8s manifests
kubeval monitoring/prometheus-rules.yaml

# YAML lint
yamllint monitoring/**/*.yaml

# Prometheus rule test (if promtool available)
promtool check rules monitoring/alerts/acgs2-security-rules.yaml

# Grafana json validate (via UI or grafana-cli)
grafana-cli plugins install grafana-simple-json-datasource
# Import and check panels

# Test alerts in Prometheus UI
# Query exprs, check firing alerts
```

## Alertmanager PagerDuty Integration

Ensure Alertmanager config has receiver:

```yaml
receivers:
- name: pagerduty
  pagerduty_configs:
  - service_key: $PAGERDUTY_KEY
    description: '{{ template "default.description" . }}'
```

Route critical/warning to pagerduty.

## SLO Dashboard Features

- MACI/TLS/RBAC rate graphs
- Error/violation rate gauges
- SLO burn rate (5m/1h)
- Error budget remaining (30d projection)
- Uptime heatmap
- Alert status table

Files created:
- `monitoring/prometheus-rules.yaml` (CRD)
- `monitoring/alerts/acgs2-security-rules.yaml` (plain)
- `monitoring/grafana-dashboards-acgs2-security-slo.json` (to be created)
- This document

All compatible with existing prometheus.yml rule_files and Helm TLS updates from previous subtask.
