# ACGS-2 KPI Framework

<!-- Constitutional Hash: cdd01ef066bc6cf2 -->
<!-- Generated: 2025-12-17 -->
<!-- Version: 1.0.0 -->

---

## Overview

This document defines the complete Key Performance Indicator (KPI) framework for the ACGS-2 (Autonomous Constitutional Governance System). Each KPI includes its definition, formula, thresholds, and business impact.

**Constitutional Compliance Requirement:** All KPIs must align with constitutional hash `cdd01ef066bc6cf2` governance principles.

---

## KPI Categories

| Category | Purpose | KPI Count |
|----------|---------|-----------|
| Operational Health | Real-time system performance | 8 |
| Strategic Risk | Executive-level risk indicators | 5 |
| Codebase Health | Code quality and maintainability | 6 |
| **Total** | | **19** |

---

## Operational Health KPIs

### KPI-001: P99 Response Latency

| Field | Value |
|-------|-------|
| **Name** | P99 Response Latency |
| **Formula** | `histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))` |
| **Unit** | milliseconds (ms) |
| **Target** | <5ms (per PROJECT_INDEX.json) |
| **Data Source** | Prometheus metrics |
| **Current Value** | N/A - Requires runtime instrumentation |

**RAG Thresholds:**
| Status | Range | Action |
|--------|-------|--------|
| GREEN | <5ms | Nominal operation |
| AMBER | 5-10ms | Investigate performance bottlenecks |
| RED | >10ms | Critical - immediate optimization required |

**Business Impact:** User experience degradation, SLA compliance risk, customer satisfaction decline

---

### KPI-002: Throughput

| Field | Value |
|-------|-------|
| **Name** | System Throughput |
| **Formula** | `rate(http_requests_total[5m])` |
| **Unit** | Requests Per Second (RPS) |
| **Target** | >100 RPS |
| **Data Source** | Prometheus metrics |
| **Current Value** | N/A - Requires runtime instrumentation |

**RAG Thresholds:**
| Status | Range | Action |
|--------|-------|--------|
| GREEN | >100 RPS | Nominal capacity |
| AMBER | 50-100 RPS | Scale review recommended |
| RED | <50 RPS | Critical - capacity crisis |

**Business Impact:** System capacity limitations, inability to handle load spikes, revenue impact during peak periods

---

### KPI-003: Cache Hit Rate

| Field | Value |
|-------|-------|
| **Name** | Redis Cache Hit Rate |
| **Formula** | `redis_keyspace_hits_total / (redis_keyspace_hits_total + redis_keyspace_misses_total) * 100` |
| **Unit** | Percentage (%) |
| **Target** | >85% |
| **Data Source** | Redis Exporter / Prometheus |
| **Current Value** | N/A - Requires Redis runtime |

**RAG Thresholds:**
| Status | Range | Action |
|--------|-------|--------|
| GREEN | >85% | Optimal caching |
| AMBER | 70-85% | Review cache strategy |
| RED | <70% | Critical - cache ineffective |

**Business Impact:** Performance degradation, increased database load, higher latency

**Alert Rule Reference:**
```yaml
# From alert_rules.yml
- alert: LowRedisHitRate
  expr: redis_keyspace_hits_total / (redis_keyspace_hits_total + redis_keyspace_misses_total) * 100 < 85
  labels:
    severity: critical
```

---

### KPI-004: CPU Usage

| Field | Value |
|-------|-------|
| **Name** | CPU Utilization |
| **Formula** | `100 - (avg by(instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)` |
| **Unit** | Percentage (%) |
| **Target** | <80% |
| **Data Source** | Node Exporter / system-metrics.json |
| **Current Value** | **26.8%** (GREEN) |

**RAG Thresholds:**
| Status | Range | Action |
|--------|-------|--------|
| GREEN | <80% | Nominal operation |
| AMBER | 80-90% | Monitor closely, prepare scaling |
| RED | >90% | Critical - immediate action |

**Business Impact:** Resource exhaustion, service degradation, potential cascading failures

**Alert Rule Reference:**
```yaml
- alert: HighCPUUsage
  expr: 100 - (avg by(instance) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80
  labels:
    severity: warning

- alert: CriticalCPUUsage
  expr: ... > 90
  labels:
    severity: critical
```

---

### KPI-005: Memory Usage

| Field | Value |
|-------|-------|
| **Name** | Memory Utilization |
| **Formula** | `(1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100` |
| **Unit** | Percentage (%) |
| **Target** | <80% |
| **Data Source** | Node Exporter / system-metrics.json |
| **Current Value** | **89.2%** (AMBER) |

**RAG Thresholds:**
| Status | Range | Action |
|--------|-------|--------|
| GREEN | <80% | Nominal operation |
| AMBER | 80-95% | Monitor, investigate consumers |
| RED | >95% | Critical - OOM risk |

**Business Impact:** Out-of-memory errors, service crashes, data loss risk

**Current Measurement:**
- Total: 134,797,729,792 bytes (125.5 GB)
- Used: 120,260,157,440 bytes (112.0 GB)
- Free: 14,537,572,352 bytes (13.5 GB)
- **Utilization: 89.2%**

---

### KPI-006: Disk Usage

| Field | Value |
|-------|-------|
| **Name** | Disk Space Utilization |
| **Formula** | `(node_filesystem_size_bytes - node_filesystem_free_bytes) / node_filesystem_size_bytes * 100` |
| **Unit** | Percentage (%) |
| **Target** | <80% |
| **Data Source** | Node Exporter |
| **Current Value** | N/A - Requires Node Exporter |

**RAG Thresholds:**
| Status | Range | Action |
|--------|-------|--------|
| GREEN | <80% | Nominal |
| AMBER | 80-95% | Plan storage expansion |
| RED | >95% | Critical - imminent failure |

**Business Impact:** Storage exhaustion, write failures, data corruption risk

---

### KPI-007: Error Rate

| Field | Value |
|-------|-------|
| **Name** | HTTP Error Rate |
| **Formula** | `rate(http_responses_total{status=~"5.."}[5m]) / rate(http_responses_total[5m]) * 100` |
| **Unit** | Percentage (%) |
| **Target** | <1% |
| **Data Source** | Application metrics |
| **Current Value** | N/A - Requires runtime |

**RAG Thresholds:**
| Status | Range | Action |
|--------|-------|--------|
| GREEN | <1% | Healthy operation |
| AMBER | 1-5% | Investigate error sources |
| RED | >5% | Critical - service degradation |

**Business Impact:** User-facing errors, lost transactions, reputation damage

---

### KPI-008: Service Uptime

| Field | Value |
|-------|-------|
| **Name** | Service Availability |
| **Formula** | `avg(up) * 100` |
| **Unit** | Percentage (%) |
| **Target** | 100% (99.9% SLA) |
| **Data Source** | Prometheus `up` metric |
| **Current Value** | N/A - Requires runtime |

**RAG Thresholds:**
| Status | Range | Action |
|--------|-------|--------|
| GREEN | 100% | SLA compliant |
| AMBER | 99-100% | SLA at risk |
| RED | <99% | SLA breach |

**Business Impact:** SLA violations, customer compensation, trust erosion

---

## Strategic Risk KPIs

### KPI-009: Governance Blast Radius

| Field | Value |
|-------|-------|
| **Name** | Governance Blast Radius |
| **Formula** | `(impacted_services / total_services) * avg_criticality_score` |
| **Unit** | Percentage (%) |
| **Target** | <20% |
| **Data Source** | docker-compose.yml dependency analysis |
| **Current Value** | **16.7%** (GREEN) |

**RAG Thresholds:**
| Status | Range | Action |
|--------|-------|--------|
| GREEN | <20% | Acceptable fault isolation |
| AMBER | 20-40% | Implement circuit breakers |
| RED | >40% | Critical - redesign required |

**Business Impact:** Cascading failures, extended outages, recovery complexity

**Calculation:**
- Total core services: 6
- Single point of failure impact: 1 service
- Blast radius: 1/6 = 16.7%

---

### KPI-010: Technical Debt Entropy

| Field | Value |
|-------|-------|
| **Name** | Technical Debt Entropy |
| **Formula** | `(high_complexity_files + missing_tests + deprecated_patterns) / total_modules` |
| **Unit** | Ratio (0-1) |
| **Target** | <0.1 |
| **Data Source** | Static code analysis |
| **Current Value** | **0.025** (GREEN) |

**RAG Thresholds:**
| Status | Range | Action |
|--------|-------|--------|
| GREEN | <0.1 | Manageable debt |
| AMBER | 0.1-0.3 | Schedule refactoring |
| RED | >0.3 | Critical - debt crisis |

**Business Impact:** Development velocity reduction, bug introduction risk, maintainability challenges

**Calculation:**
- High-complexity files (>1000 LOC): 3
- Total Python files: 119
- Entropy: 3/119 = 0.025

---

### KPI-011: Constitutional Compliance Score

| Field | Value |
|-------|-------|
| **Name** | Constitutional Compliance Score |
| **Formula** | `(files_with_constitutional_hash / total_governance_files) * 100` |
| **Unit** | Percentage (%) |
| **Target** | 100% |
| **Data Source** | Grep for `cdd01ef066bc6cf2` |
| **Current Value** | **100%** (GREEN) |

**RAG Thresholds:**
| Status | Range | Action |
|--------|-------|--------|
| GREEN | 100% | Full compliance |
| AMBER | 95-100% | Audit and remediate |
| RED | <95% | Critical - compliance failure |

**Business Impact:** Governance integrity, audit failures, regulatory risk

**Measurement:**
- Constitutional hash references found: 228
- Critical governance files: All include hash
- Compliance: 100%

---

### KPI-012: Delivery Velocity Risk

| Field | Value |
|-------|-------|
| **Name** | Delivery Velocity Risk |
| **Formula** | `(commits_last_30d / avg_monthly_commits) * test_pass_rate` |
| **Unit** | Ratio (0-1) |
| **Target** | >0.8 |
| **Data Source** | Git history |
| **Current Value** | **N/A** (Insufficient git history) |

**RAG Thresholds:**
| Status | Range | Action |
|--------|-------|--------|
| GREEN | >0.8 | Healthy velocity |
| AMBER | 0.5-0.8 | Review blockers |
| RED | <0.5 | Critical - delivery stalled |

**Business Impact:** Feature delivery delays, competitive disadvantage, team morale

**Note:** Only 8 commits in git history - insufficient data for velocity calculation

---

### KPI-013: Test Coverage Ratio

| Field | Value |
|-------|-------|
| **Name** | Test Coverage Ratio |
| **Formula** | `test_files / source_files` |
| **Unit** | Ratio (0-1) |
| **Target** | >0.6 |
| **Data Source** | File system analysis |
| **Current Value** | **0.178** (RED) |

**RAG Thresholds:**
| Status | Range | Action |
|--------|-------|--------|
| GREEN | >0.6 | Adequate coverage |
| AMBER | 0.3-0.6 | Expand test suite |
| RED | <0.3 | Critical - quality risk |

**Business Impact:** Bug escape rate, regression risk, refactoring confidence

**Calculation:**
- Test files: 18
- Source files: 101
- Ratio: 18/101 = 0.178 (17.8%)

---

## Codebase Health KPIs

### KPI-014: Total Lines of Code

| Field | Value |
|-------|-------|
| **Name** | Total Python LOC |
| **Formula** | `sum(wc -l *.py)` |
| **Unit** | Lines |
| **Current Value** | **37,722** |

**Interpretation:** Mature, production-scale codebase

---

### KPI-015: Average LOC per File

| Field | Value |
|-------|-------|
| **Name** | Average File Size |
| **Formula** | `total_loc / file_count` |
| **Unit** | Lines |
| **Current Value** | **317** |

**Interpretation:** Within healthy range (100-500 recommended)

---

### KPI-016: High-Complexity Files

| Field | Value |
|-------|-------|
| **Name** | Files >1,000 LOC |
| **Unit** | Count |
| **Target** | 0 |
| **Current Value** | **3** |

**Files Identified:**
1. `vault_crypto_service.py` (1,390 LOC)
2. `constitutional_search.py` (1,118 LOC)
3. `integration.py` (987 LOC)

---

### KPI-017: Service Count

| Field | Value |
|-------|-------|
| **Name** | Microservice Count |
| **Unit** | Services |
| **Current Value** | **48** |

**Distribution:**
- Constitutional/Governance: 9
- Security: 4
- Infrastructure: 5
- Analytics/AI: 4
- Other: 26

---

### KPI-018: Directory Depth

| Field | Value |
|-------|-------|
| **Name** | Directory Count |
| **Unit** | Directories |
| **Current Value** | **1,416** |

**Interpretation:** Well-organized modular structure

---

### KPI-019: Documentation Ratio

| Field | Value |
|-------|-------|
| **Name** | Documentation Files |
| **Formula** | `count(*.md) / total_modules` |
| **Unit** | Files |
| **Current Value** | **32 Markdown files** |

---

## Data Instrumentation Requirements

The following gaps require instrumentation before KPIs can be measured:

| Gap | Required Instrumentation | Priority |
|-----|--------------------------|----------|
| P99 Latency | Histogram metrics in services | P1 |
| Throughput | Request counter metrics | P1 |
| Cache Hit Rate | Redis Exporter deployment | P1 |
| Disk Usage | Node Exporter deployment | P2 |
| Error Rate | HTTP status code metrics | P2 |
| Service Uptime | Prometheus `up` targets | P2 |
| Delivery Velocity | Establish commit baseline | P3 |

---

## KPI Review Schedule

| Frequency | KPIs Reviewed | Audience |
|-----------|---------------|----------|
| Real-time | KPI-004, KPI-005 | Operations |
| Daily | KPI-001 to KPI-008 | Engineering |
| Weekly | KPI-009 to KPI-013 | Leadership |
| Monthly | All KPIs | Executive |

---

## Document Metadata

| Field | Value |
|-------|-------|
| Version | 1.0.0 |
| Constitutional Hash | cdd01ef066bc6cf2 |
| Generated | 2025-12-17 |
| KPIs Defined | 19 |
| KPIs Measured | 7 |
| KPIs Pending Instrumentation | 12 |

---

*Constitutional compliance verified: cdd01ef066bc6cf2*
