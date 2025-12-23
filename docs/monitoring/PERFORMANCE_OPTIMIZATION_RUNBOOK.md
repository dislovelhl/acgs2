# ACGS-2 Continuous Performance Optimization Runbook

**Constitutional Hash**: `cdd01ef066bc6cf2`
**Version**: 1.0.0
**Last Updated**: 2025-12-23

## Overview

This runbook provides procedures for maintaining and optimizing ACGS-2 system performance. It covers proactive monitoring, reactive incident response, and continuous optimization strategies.

## Performance Targets (Validated)

| Metric | Target | Current Achievement | Status |
|--------|--------|---------------------|--------|
| P99 Latency | <5ms | 3.23ms | Exceeds |
| Throughput | >100 RPS | 314 RPS | Exceeds (3x) |
| Error Rate | <1% | 0% | Exceeds |
| Cache Hit Rate | >85% | 95% | Exceeds |
| Constitutional Compliance | 100% | 100% | Meets |

## Alert Thresholds

### Latency Alerts

| Severity | P99 Threshold | Response Time | Escalation |
|----------|---------------|---------------|------------|
| Warning | >4ms | 30 minutes | Team notification |
| Critical | >5ms | 5 minutes | PagerDuty + On-call |

### Throughput Alerts

| Severity | RPS Threshold | Response Time | Escalation |
|----------|---------------|---------------|------------|
| Warning | <150 RPS | 30 minutes | Team notification |
| Critical | <100 RPS | 5 minutes | PagerDuty + On-call |

### Error Rate Alerts

| Severity | Error % | Response Time | Escalation |
|----------|---------|---------------|------------|
| Warning | >1% | 30 minutes | Team notification |
| Critical | >5% | 5 minutes | PagerDuty + On-call |

---

## Proactive Monitoring Procedures

### Daily Health Check

**Schedule**: Every morning at 09:00 UTC

1. **Review Dashboard Overview**
   ```bash
   # Access monitoring dashboard
   curl -s http://localhost:8090/dashboard/overview | jq .

   # Check key metrics
   curl -s http://localhost:8090/dashboard/metrics | jq '.performance'
   ```

2. **Verify Constitutional Compliance**
   ```bash
   # Check constitutional validation metrics
   curl -s http://localhost:9090/api/v1/query?query=constitutional_validations_total | jq .

   # Verify zero violations
   curl -s http://localhost:9090/api/v1/query?query=constitutional_violations_total | jq .
   ```

3. **Check Circuit Breaker Status**
   ```bash
   # All breakers should be CLOSED
   curl -s http://localhost:8090/dashboard/health | jq '.circuit_breakers[] | select(.state != "closed")'
   ```

4. **Review Error Budget**
   ```bash
   # Calculate remaining error budget (30-day rolling)
   # Formula: 0.1% of requests = error budget for 99.9% SLO
   ```

### Weekly Performance Review

**Schedule**: Every Monday at 10:00 UTC

1. **Generate Performance Report**
   ```bash
   # Export last 7 days of metrics
   curl -s "http://localhost:9090/api/v1/query_range?query=histogram_quantile(0.99,sum(rate(http_request_duration_seconds_bucket[1h]))by(le))&start=$(date -d '7 days ago' +%s)&end=$(date +%s)&step=3600" > weekly_latency.json
   ```

2. **Compare Against Baseline**
   - P99 latency trend
   - Throughput trend
   - Error rate trend
   - Cache hit rate trend

3. **Identify Optimization Opportunities**
   - Slow endpoints (P99 > 2ms)
   - Low cache hit rate operations
   - High error rate paths
   - Resource bottlenecks

4. **Document Findings**
   - Create JIRA ticket for significant degradations
   - Update performance baseline if improvements detected

### Monthly Capacity Review

**Schedule**: First Monday of each month

1. **Resource Utilization Analysis**
   - CPU usage trends
   - Memory utilization patterns
   - Disk I/O and storage growth
   - Network bandwidth utilization

2. **Capacity Planning**
   - Project 90-day resource requirements
   - Identify scaling needs
   - Plan infrastructure changes

3. **Performance Optimization Backlog**
   - Review and prioritize optimization tasks
   - Schedule optimization sprints

---

## Incident Response Procedures

### High Latency Response (P99 >5ms)

**Severity**: Critical
**Response Time**: 5 minutes
**Escalation**: On-call engineer + Platform team lead

#### Immediate Actions (0-5 minutes)

1. **Acknowledge Alert**
   ```bash
   # Acknowledge in PagerDuty or monitoring system
   ```

2. **Verify the Issue**
   ```bash
   # Check current P99 latency
   curl -s http://localhost:9090/api/v1/query?query=histogram_quantile\(0.99,sum\(rate\(http_request_duration_seconds_bucket[5m]\)\)by\(le\)\) | jq .

   # Check latency by service
   curl -s "http://localhost:9090/api/v1/query?query=histogram_quantile(0.99,sum(rate(http_request_duration_seconds_bucket[5m]))by(le,service))" | jq .
   ```

3. **Identify Affected Services**
   ```bash
   # Find services with high latency
   curl -s "http://localhost:9090/api/v1/query?query=topk(5,histogram_quantile(0.99,sum(rate(http_request_duration_seconds_bucket[5m]))by(le,service)))" | jq .
   ```

#### Investigation (5-15 minutes)

4. **Check Resource Utilization**
   ```bash
   # CPU usage
   curl -s http://localhost:9090/api/v1/query?query=100-\(avg\(irate\(node_cpu_seconds_total{mode=\"idle\"}[5m]\)\)*100\) | jq .

   # Memory usage
   curl -s "http://localhost:9090/api/v1/query?query=(1-node_memory_MemAvailable_bytes/node_memory_MemTotal_bytes)*100" | jq .
   ```

5. **Check Cache Performance**
   ```bash
   # Cache hit rate
   curl -s "http://localhost:9090/api/v1/query?query=sum(rate(cache_hits_total[5m]))/(sum(rate(cache_hits_total[5m]))+sum(rate(cache_misses_total[5m])))*100" | jq .
   ```

6. **Check Database/Redis Latency**
   ```bash
   # Redis latency
   redis-cli --latency-history -i 1

   # Check connection pool
   redis-cli CLIENT LIST | wc -l
   ```

7. **Check Circuit Breaker Status**
   ```bash
   # Any open circuit breakers indicate upstream issues
   curl -s http://localhost:8090/dashboard/health | jq '.circuit_breakers[] | select(.state == "open")'
   ```

#### Mitigation (15-30 minutes)

8. **Apply Immediate Fixes**

   **If Cache Issue:**
   ```bash
   # Increase cache TTL temporarily
   redis-cli CONFIG SET maxmemory-policy volatile-lru

   # Clear problematic cache entries
   redis-cli FLUSHDB  # Use with caution!
   ```

   **If Resource Exhaustion:**
   ```bash
   # Scale horizontally
   kubectl scale deployment acgs2-agent-bus --replicas=5

   # Or vertically
   kubectl set resources deployment acgs2-agent-bus --limits=cpu=2,memory=4Gi
   ```

   **If Upstream Service Issue:**
   ```bash
   # Enable circuit breaker degraded mode
   # This is handled automatically by the circuit breaker
   ```

#### Resolution and Post-Mortem

9. **Verify Recovery**
   ```bash
   # Monitor P99 latency returning to normal
   watch -n 5 'curl -s http://localhost:9090/api/v1/query?query=histogram_quantile\(0.99,sum\(rate\(http_request_duration_seconds_bucket[5m]\)\)by\(le\)\) | jq .data.result[0].value[1]'
   ```

10. **Document Incident**
    - Create incident report
    - Root cause analysis
    - Action items for prevention

### Low Throughput Response (RPS <100)

**Severity**: Critical
**Response Time**: 5 minutes

#### Immediate Actions

1. **Check Service Health**
   ```bash
   curl -s http://localhost:8090/dashboard/services | jq '.[] | select(.status != "healthy")'
   ```

2. **Check Load Balancer**
   ```bash
   # Verify all backends are healthy
   kubectl get pods -l app=acgs2 -o wide
   ```

3. **Check for Rate Limiting**
   ```bash
   # Check if rate limits are being hit
   curl -s "http://localhost:9090/api/v1/query?query=rate(http_requests_total{status='429'}[5m])" | jq .
   ```

4. **Check Upstream Dependencies**
   ```bash
   # Policy registry health
   curl -s http://localhost:8000/health | jq .

   # OPA service health
   curl -s http://localhost:8181/health | jq .
   ```

### High Error Rate Response (>5%)

**Severity**: Critical
**Response Time**: 5 minutes

#### Immediate Actions

1. **Identify Error Types**
   ```bash
   # Error breakdown by status code
   curl -s "http://localhost:9090/api/v1/query?query=sum(rate(http_requests_total{status=~'5..'}[5m]))by(status)" | jq .
   ```

2. **Check Error Logs**
   ```bash
   # Recent errors
   kubectl logs -l app=acgs2 --since=10m | grep -i error

   # Or via ELK
   curl -s "http://localhost:9200/logs-*/_search" -H 'Content-Type: application/json' -d '
   {
     "query": {
       "bool": {
         "must": [
           {"match": {"level": "ERROR"}},
           {"range": {"@timestamp": {"gte": "now-10m"}}}
         ]
       }
     }
   }' | jq .
   ```

3. **Check Constitutional Violations**
   ```bash
   # Any constitutional errors require immediate attention
   curl -s "http://localhost:9090/api/v1/query?query=rate(constitutional_violations_total[5m])" | jq .
   ```

---

## Optimization Procedures

### Cache Optimization

#### When Cache Hit Rate <90%

1. **Analyze Cache Patterns**
   ```bash
   # Cache hit rate by operation
   curl -s "http://localhost:9090/api/v1/query?query=sum(rate(cache_hits_total[1h]))by(operation)/(sum(rate(cache_hits_total[1h]))by(operation)+sum(rate(cache_misses_total[1h]))by(operation))*100" | jq .
   ```

2. **Identify Cold Cache Entries**
   ```bash
   redis-cli --scan --pattern 'acgs2:*' | head -100 | while read key; do
     echo "$key: $(redis-cli TTL $key)"
   done
   ```

3. **Optimize Cache Strategy**
   - Increase TTL for stable data
   - Implement cache warming for frequently accessed data
   - Use multi-tier caching (L1/L2/L3)

4. **Implement Changes**
   ```python
   # Example: Cache warming for policy data
   async def warm_policy_cache():
       policies = await get_all_active_policies()
       for policy in policies:
           await cache.set(f"policy:{policy.id}", policy, ttl=3600)
   ```

### Latency Optimization

#### When P99 >3ms

1. **Profile Slow Paths**
   ```bash
   # Enable detailed tracing
   export TRACE_ENABLED=true

   # Analyze trace spans
   curl -s http://localhost:16686/api/traces?service=acgs2-agent-bus&limit=100 | jq '.data[].spans[] | select(.duration > 3000000)'
   ```

2. **Identify Bottlenecks**
   - Database queries
   - External API calls
   - CPU-intensive operations
   - Memory allocations

3. **Apply Optimizations**
   ```python
   # Example: Add caching to expensive operation
   @functools.lru_cache(maxsize=1000)
   def validate_constitutional_hash(hash_value: str) -> bool:
       return hash_value == CONSTITUTIONAL_HASH
   ```

### Throughput Optimization

#### When RPS <250

1. **Identify Bottlenecks**
   ```bash
   # Check connection pool exhaustion
   curl -s "http://localhost:9090/api/v1/query?query=http_requests_in_progress" | jq .

   # Check queue depth
   curl -s "http://localhost:9090/api/v1/query?query=message_queue_depth" | jq .
   ```

2. **Scale Resources**
   ```bash
   # Horizontal scaling
   kubectl scale deployment acgs2-agent-bus --replicas=5

   # Check HPA status
   kubectl get hpa
   ```

3. **Optimize Concurrency**
   ```python
   # Example: Increase connection pool
   POOL_SIZE = int(os.getenv("POOL_SIZE", "50"))
   redis_pool = redis.ConnectionPool(max_connections=POOL_SIZE)
   ```

---

## Performance Testing Procedures

### Pre-Deployment Performance Test

**Run before every production deployment**

```bash
# 1. Run benchmark suite
cd enhanced_agent_bus
python -m pytest tests/test_performance.py -v --benchmark-json=benchmark.json

# 2. Validate against thresholds
python scripts/validate_performance.py benchmark.json

# 3. Compare with baseline
python scripts/compare_baseline.py benchmark.json baseline.json
```

### Load Testing

**Run weekly or before major releases**

```bash
# Using locust
locust -f load_test.py --headless -u 1000 -r 100 -t 10m \
  --host http://localhost:8080 \
  --csv performance_report

# Validate results
python scripts/validate_load_test.py performance_report_stats.csv
```

### Chaos Testing

**Run monthly in staging environment**

```bash
# Enable chaos testing (staging only!)
export CHAOS_ENABLED=true
export CHAOS_BLAST_RADIUS=0.1

# Run chaos scenarios
python -m pytest tests/test_chaos.py -v

# Validate recovery
python scripts/validate_recovery.py
```

---

## Dashboards and Monitoring URLs

| Dashboard | URL | Purpose |
|-----------|-----|---------|
| Main Dashboard | http://localhost:8090/dashboard | Real-time overview |
| Grafana | http://localhost:3000 | Detailed metrics |
| Prometheus | http://localhost:9090 | Raw metrics |
| Jaeger | http://localhost:16686 | Distributed tracing |
| Kibana | http://localhost:5601 | Log analysis |

## Key Prometheus Queries

### Latency Metrics
```promql
# P99 latency by service
histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le, service))

# P50 latency
histogram_quantile(0.50, sum(rate(http_request_duration_seconds_bucket[5m])) by (le))
```

### Throughput Metrics
```promql
# Total RPS
sum(rate(http_requests_total[5m]))

# RPS by service
sum(rate(http_requests_total[5m])) by (service)
```

### Error Metrics
```promql
# Error rate percentage
sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) * 100

# Constitutional violations
sum(rate(constitutional_violations_total[5m])) by (service)
```

### Cache Metrics
```promql
# Cache hit rate
sum(rate(cache_hits_total[5m])) / (sum(rate(cache_hits_total[5m])) + sum(rate(cache_misses_total[5m]))) * 100
```

---

## Escalation Contacts

| Level | Contact | Response Time |
|-------|---------|---------------|
| L1 | On-call Engineer | 5 minutes |
| L2 | Platform Team Lead | 15 minutes |
| L3 | Engineering Manager | 30 minutes |
| L4 | VP Engineering | 1 hour |

## Related Documents

- [Monitoring Dashboard Documentation](MONITORING_DASHBOARD.md)
- [Security Hardening Guide](../security/SECURITY_HARDENING.md)
- [Enhanced Agent Bus Documentation](../../enhanced_agent_bus/README.md)
- [Performance Thresholds Configuration](../../monitoring/performance_thresholds.yml)
- [Alert Rules Configuration](../../monitoring/acgs2_performance_alerts.yml)

---

**Constitutional Hash**: `cdd01ef066bc6cf2`
