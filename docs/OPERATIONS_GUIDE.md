# 🚀 ACGS-2 Operations Guide

> **Production Excellence Framework for Enterprise AI Governance**

## 📋 Overview

This guide provides comprehensive operational procedures for maintaining ACGS-2's production excellence through automated quality assurance, performance monitoring, and continuous improvement.

## 🏗️ Operational Components

### 1. **Quality Gates & CI/CD**
- **Pre-commit Hooks**: Automated code quality checks
- **GitHub Actions**: CI/CD pipeline with quality validation
- **Quality Gate Script**: Manual and automated quality assessment

### 2. **Performance Monitoring**
- **Automated Regression Testing**: Daily performance validation
- **Performance Dashboards**: Real-time metrics visualization
- **Alert System**: Performance degradation detection

### 3. **Chaos Engineering**
- **Production Resilience Testing**: Automated failure injection
- **Recovery Validation**: System recovery capability testing
- **Blast Radius Assessment**: Impact analysis for failures

### 4. **Test Infrastructure**
- **Optimized Test Suite**: Focused, maintainable test modules
- **Parallel Execution**: Faster CI/CD with distributed testing
- **Coverage Tracking**: Test effectiveness monitoring

---

## 🔧 Setup & Configuration

### **Step 1: Pre-commit Hooks Setup**

```bash
# Install pre-commit globally
pipx install pre-commit

# Install hooks in repository
cd /path/to/acgs2
pre-commit install

# Test hooks (run on all files)
pre-commit run --all-files
```

**Pre-commit Configuration:**
- ✅ **Ruff Linting**: Code style and error detection
- ✅ **MyPy Type Checking**: Type safety validation
- ✅ **Security Scanning**: Vulnerability detection
- ✅ **ACGS-2 Quality Gates**: Custom quality checks
- ✅ **Commit Message Validation**: Conventional commit format

### **Step 2: Performance Monitoring Setup**

```bash
# Run automated setup
./scripts/setup_performance_monitoring.sh

# This configures:
# - Daily performance regression testing (cron)
# - Weekly quality gate monitoring (cron)
# - Performance dashboard generation
# - Alert system configuration
```

### **Step 3: Quality Dashboard Setup**

```bash
# Generate initial quality metrics
python scripts/quality_metrics_monitor.py

# Create interactive dashboards
python scripts/create_quality_dashboard.py

# View dashboard
open reports/dashboard/index.html
```

---

## 📊 Daily Operations

### **Morning Health Check**

```bash
# 1. Check service health
curl -f http://localhost:8000/health  # Agent Bus
curl -f http://localhost:8080/health  # API Gateway
curl -f http://localhost:8181/health  # OPA

# 2. Run quality gates
./scripts/quality_gate.sh

# 3. Check performance metrics
./scripts/performance_regression_test.sh

# 4. Review alerts
cat reports/monitoring/performance_alerts.txt
```

### **Automated Monitoring**

**Cron Jobs Configured:**
```bash
# Daily performance regression
@daily /path/to/acgs2/scripts/performance_regression_test.sh

# Weekly quality assessment
@weekly /path/to/acgs2/scripts/quality_gate.sh
```

**Log Locations:**
- Performance logs: `reports/monitoring/performance_cron.log`
- Quality logs: `reports/monitoring/quality_cron.log`
- Alerts: `reports/monitoring/performance_alerts.txt`

---

## 🚨 Incident Response

### **Performance Degradation Alert**

```bash
# 1. Check recent performance data
tail -20 reports/monitoring/performance_cron.log

# 2. Run detailed performance analysis
python scripts/performance_dashboard.py

# 3. Check service metrics
docker stats acgs2-agent-bus-1 acgs2-api-gateway-1

# 4. Review recent changes
git log --oneline -10

# 5. Run chaos test to verify resilience
python acgs2-core/chaos/experiments/advanced-chaos-scenarios.py
```

### **Quality Gate Failure**

```bash
# 1. Check quality gate output
./scripts/quality_gate.sh

# 2. Identify failing components
# - Syntax errors: Fix immediately
# - Bare except clauses: Add specific exception handling
# - Print statements: Replace with logging

# 3. Run pre-commit hooks
pre-commit run --all-files

# 4. Update quality metrics
python scripts/quality_metrics_monitor.py
```

### **Test Suite Issues**

```bash
# 1. Check test execution
cd acgs2-core/enhanced_agent_bus
python -m pytest tests/ -v

# 2. Run test optimization analysis
python ../../../scripts/optimize_test_files.py

# 3. Split large test files if needed
python ../../../scripts/split_test_files.py
```

---

## 📈 Performance Management

### **Performance Targets**

| Metric | Target | Alert Threshold | Action |
|--------|--------|-----------------|---------|
| P99 Latency | < 0.328ms | > 0.5ms | 🚨 Critical |
| Throughput | > 2,605 RPS | < 2,000 RPS | 🚨 Critical |
| Cache Hit Rate | > 95% | < 90% | ⚠️ Warning |
| Memory Usage | < 4MB/pod | > 6MB/pod | ⚠️ Warning |
| CPU Usage | < 75% | > 85% | ⚠️ Warning |

### **Performance Tuning**

```bash
# 1. Run performance benchmark
cd acgs2-core/scripts
python performance_benchmark.py

# 2. Analyze bottlenecks
python ../../scripts/performance_dashboard.py

# 3. Optimize identified issues
# - Database query optimization
# - Cache configuration tuning
# - Async processing improvements

# 4. Re-run benchmark to validate improvements
python performance_benchmark.py
```

---

## 🎭 Chaos Engineering Operations

### **Scheduled Chaos Testing**

```bash
# Weekly chaos testing
python acgs2-core/chaos/experiments/advanced-chaos-scenarios.py

# Network chaos (monthly)
kubectl apply -f acgs2-core/chaos/experiments/network-chaos.yaml
```

### **Chaos Test Scenarios**

1. **Single Service Crash**
   - Tests: Automatic recovery, service isolation
   - Duration: 60 seconds
   - Success Criteria: < 30s recovery, >95% availability

2. **Network Partition**
   - Tests: System resilience, data consistency
   - Duration: 120 seconds
   - Success Criteria: <60s recovery, >80% availability

3. **Resource Exhaustion**
   - Tests: Graceful degradation, resource limits
   - Duration: 90 seconds
   - Success Criteria: <45s recovery, >85% availability

### **Post-Chaos Analysis**

```bash
# Review chaos test results
cat reports/chaos/scenario_*_*.json

# Update recovery procedures based on findings
# Adjust chaos test frequency based on results
```

---

## 📊 Quality Metrics Dashboard

### **Dashboard Components**

1. **Overview Dashboard**
   - Current quality scores
   - Performance metrics
   - Security status
   - Test coverage

2. **Trends Dashboard**
   - Historical performance data
   - Code quality evolution
   - Coverage trends
   - Security posture changes

3. **Alerts Dashboard**
   - Active alerts and warnings
   - Recent incidents
   - Trend analysis

### **Quality Score Calculation**

```
Quality Score = 100 - penalties

Penalties:
- Coverage < 80%: -20 points
- P99 Latency > 0.5ms: -15 points
- Security vulnerabilities: -5 points each
- Syntax errors: -2 points each
- Lint errors: -0.1 points each
```

### **Score Interpretation**

- **90-100**: Excellent quality
- **80-89**: Good quality
- **70-79**: Acceptable, needs attention
- **60-69**: Requires improvement
- **<60**: Critical issues, immediate action required

---

## 🔄 Continuous Improvement

### **Weekly Review Process**

```bash
# 1. Review quality metrics
python scripts/quality_metrics_monitor.py

# 2. Analyze performance trends
python scripts/performance_dashboard.py

# 3. Check chaos testing results
ls reports/chaos/

# 4. Review test coverage reports
cat reports/coverage/coverage_summary.txt

# 5. Update thresholds if needed
vim reports/monitoring/config.json
```

### **Monthly Deep Dive**

1. **Performance Optimization**
   - Review slowest endpoints
   - Optimize database queries
   - Update cache strategies

2. **Security Hardening**
   - Update dependencies
   - Review access patterns
   - Update security policies

3. **Test Suite Enhancement**
   - Add missing test coverage
   - Optimize test execution time
   - Update test data

4. **Chaos Engineering Evolution**
   - Add new failure scenarios
   - Improve recovery procedures
   - Update blast radius assessments

### **Quarterly Architecture Review**

1. **Scalability Assessment**
   - Review performance under load
   - Plan capacity upgrades
   - Update architecture diagrams

2. **Technology Stack Updates**
   - Update framework versions
   - Evaluate new tools/libraries
   - Plan migration strategies

---

## 🆘 Emergency Procedures

### **System Outage**

```bash
# 1. Check service status
docker ps | grep acgs2

# 2. Restart services
docker-compose -f acgs2-core/docker-compose.dev.yml restart

# 3. Check logs
docker-compose -f acgs2-core/docker-compose.dev.yml logs

# 4. Run health checks
./scripts/health_check.sh

# 5. Notify stakeholders
# Include: outage duration, impact, root cause, mitigation
```

### **Performance Emergency**

```bash
# 1. Immediate performance check
./scripts/performance_regression_test.sh

# 2. Scale resources if needed
kubectl scale deployment acgs2-agent-bus --replicas=3

# 3. Check resource utilization
kubectl top pods

# 4. Apply emergency optimizations
# - Increase cache size
# - Reduce concurrent connections
# - Enable circuit breakers
```

### **Security Incident**

```bash
# 1. Isolate affected systems
# - Block suspicious IPs
# - Disable compromised services
# - Enable emergency mode

# 2. Assess damage
# - Check data integrity
# - Review access logs
# - Run security scans

# 3. Recovery and remediation
# - Apply security patches
# - Rotate credentials
# - Update security policies

# 4. Post-incident analysis
# - Root cause analysis
# - Update incident response procedures
# - Improve monitoring/alerting
```

---

## 📚 Command Reference

### **Quality Assurance**
```bash
# Run quality gates
./scripts/quality_gate.sh

# Check code quality
ruff check acgs2-core --select E,F,B,I

# Type checking
mypy acgs2-core --ignore-missing-imports

# Security scanning
bandit -r acgs2-core -f json
```

### **Performance Monitoring**
```bash
# Performance regression test
./scripts/performance_regression_test.sh

# Performance dashboard
python scripts/performance_dashboard.py

# Quality metrics
python scripts/quality_metrics_monitor.py
```

### **Testing**
```bash
# Run test suite
cd acgs2-core/enhanced_agent_bus && python -m pytest tests/ -v

# Test optimization analysis
python ../../../scripts/optimize_test_files.py

# Split large test files
python ../../../scripts/split_test_files.py
```

### **Chaos Engineering**
```bash
# Run chaos scenarios
python acgs2-core/chaos/experiments/advanced-chaos-scenarios.py

# Network chaos
kubectl apply -f acgs2-core/chaos/experiments/network-chaos.yaml
```

---

## 🎯 Success Metrics

### **Operational Excellence Targets**

- **Uptime**: 99.9% (target), 99.95% (stretch)
- **MTTR**: < 15 minutes (target), < 5 minutes (stretch)
- **Quality Score**: > 85 (target), > 95 (stretch)
- **Performance Deviation**: < 5% from baseline
- **Test Coverage**: > 90% (target), > 95% (stretch)

### **Continuous Improvement**

- **Monthly**: Quality score improvement > 2 points
- **Quarterly**: Performance improvement > 10%
- **Annually**: Zero security incidents, 100% uptime

---

**ACGS-2 Operations Guide v2.0**
*Last Updated: January 2026*

**Maintainer**: ACGS-2 Operations Team
**Contact**: operations@acgs2.org

---

*This guide ensures ACGS-2 maintains production excellence through systematic quality assurance, performance monitoring, and continuous improvement processes.*
