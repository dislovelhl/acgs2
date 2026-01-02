# ACGS-2 Performance Benchmarking

## Overview

This directory contains comprehensive performance benchmarking tools for ACGS-2, designed to validate the system's claimed performance metrics and ensure continued performance excellence.

## Constitutional Compliance

**Constitutional Hash**: `cdd01ef066bc6cf2`

All performance benchmarks are conducted under constitutional governance, ensuring that performance optimizations do not compromise security or constitutional compliance.

## Performance Targets

Based on architecture review and system specifications:

| Metric | Target | Current Status | Validation Method |
|--------|--------|----------------|-------------------|
| P99 Latency | 0.278ms | 0.328ms (94% of target) | Async load testing |
| Throughput | 6,310 RPS | 2,605 RPS (41% of target) | Concurrent request simulation |
| Cache Hit Rate | 95% | 95% (100% of target) | Metrics endpoint analysis |
| Memory Usage | < 4MB per pod | < 4MB (100% of target) | Prometheus metrics |
| CPU Utilization | < 75% | 73.9% (99% of target) | System monitoring |

## Benchmark Scripts

### `performance_benchmark.py`

Comprehensive performance validation script that tests:

- **Latency**: P50, P95, P99 response times under various loads
- **Throughput**: Maximum sustainable requests per second
- **Resource Usage**: Memory and CPU utilization validation
- **Constitutional Compliance**: Hash validation during testing

#### Usage

```bash
# Run full benchmark suite
python performance_benchmark.py

# Run with custom configuration
python performance_benchmark.py --url http://your-service:8000 --duration 120 --users 200
```

#### Output

Generates `performance_benchmark_report.json` with:
- Detailed metrics for each test phase
- Pass/fail status against targets
- Performance recommendations
- Error analysis and debugging information

## Running Benchmarks

### Prerequisites

1. **Running ACGS-2 Service**: Ensure the agent bus is running and accessible
2. **Python Dependencies**: Install required packages:
   ```bash
   pip install aiohttp numpy tqdm requests
   ```
3. **Metrics Endpoint**: Service should expose `/metrics` endpoint for resource monitoring

### Execution Steps

1. **Start ACGS-2 Service**:
   ```bash
   cd acgs2-core
   python -m enhanced_agent_bus.agent_bus
   ```

2. **Run Benchmark**:
   ```bash
   cd scripts
   python performance_benchmark.py
   ```

3. **Analyze Results**:
   - Review console output for immediate feedback
   - Examine `performance_benchmark_report.json` for detailed analysis
   - Check recommendations for performance improvements

## Benchmark Phases

### Phase 1: Warm-up
- 50 requests to stabilize system caches
- Validates basic service availability

### Phase 2: Latency Benchmark
- 100 requests under low concurrency
- Measures P50, P95, P99 response times
- Validates sub-millisecond performance claims

### Phase 3: Throughput Benchmark
- Ramp-up testing from 1K to target RPS
- Finds maximum sustainable throughput
- Measures success rates under load

### Phase 4: Sustained Load
- 30-second continuous load test
- Validates long-term stability
- Checks for memory leaks or performance degradation

### Phase 5: Resource Validation
- Queries Prometheus metrics endpoint
- Validates memory and CPU targets
- Ensures efficient resource utilization

## Interpreting Results

### Success Criteria

- **Latency**: P99 ≤ 0.278ms
- **Throughput**: ≥ 6,310 RPS at 95%+ success rate
- **Resources**: Memory < 4MB, CPU < 75%
- **Cache**: Hit rate ≥ 95%

### Common Issues

1. **High Latency**:
   - Network configuration issues
   - Database connection pooling problems
   - Inefficient async/await patterns

2. **Low Throughput**:
   - Insufficient worker processes
   - Database connection limits
   - Message queue backlogs

3. **High Resource Usage**:
   - Memory leaks in message processing
   - Inefficient caching strategies
   - Excessive logging or metrics collection

## Performance Optimization

### Immediate Actions

1. **Enable Connection Pooling**: Configure database and Redis connection pools
2. **Optimize Async Patterns**: Review and fix blocking operations in async code
3. **Tune Garbage Collection**: Adjust Python GC settings for high-throughput workloads

### Advanced Optimizations

1. **Rust Backend Integration**: Leverage compiled Rust components for CPU-intensive operations
2. **Horizontal Scaling**: Implement pod autoscaling based on queue depth
3. **Caching Strategy**: Implement multi-level caching (L1/L2/L3)

### Monitoring Integration

The benchmarking framework integrates with existing monitoring:

- **Prometheus Metrics**: Automatic collection of performance metrics
- **Distributed Tracing**: Jaeger integration for request tracing
- **Custom Dashboards**: Grafana panels for performance monitoring

## Constitutional Performance Governance

All performance optimizations must maintain constitutional compliance:

- **Hash Validation**: Performance improvements cannot compromise security
- **Impact Assessment**: Changes require human-in-the-loop review for high-impact modifications
- **Audit Trail**: All performance changes are logged and auditable

## Continuous Performance Validation

### CI/CD Integration

```yaml
# .github/workflows/performance.yml
- name: Performance Benchmark
  run: |
    python scripts/performance_benchmark.py
    # Fail CI if performance regresses
    python scripts/check_performance_regression.py
```

### Scheduled Monitoring

```bash
# Cron job for daily performance validation
0 2 * * * /path/to/acgs2-core/scripts/performance_benchmark.py --quiet --report-only
```

## Troubleshooting

### Benchmark Failures

1. **Connection Refused**: Ensure service is running and accessible
2. **Timeout Errors**: Increase timeout values or optimize service response times
3. **High Error Rates**: Check service logs for underlying issues

### Performance Issues

1. **Memory Growth**: Use memory profiling tools to identify leaks
2. **CPU Spikes**: Profile code to find performance bottlenecks
3. **Network Latency**: Check network configuration and DNS resolution

## Future Enhancements

- **Distributed Benchmarking**: Multi-region performance validation
- **Chaos Engineering Integration**: Performance testing under failure conditions
- **ML-Based Optimization**: Automated performance tuning recommendations
- **Real User Monitoring**: Production performance validation
