# ACGS-2 Rego Policy Deployment Guide
Constitutional Hash: cdd01ef066bc6cf2

## Quick Start

### Single Instance Deployment

```bash
cd /home/dislove/document/acgs2/policies/rego

# Start OPA
docker compose up -d opa-primary

# Verify
curl http://localhost:8181/health
```

### High Availability Deployment

```bash
# Start all services
docker compose up -d

# Verify services
docker compose ps

# Check health
curl http://localhost:8180/health  # Load balancer
curl http://localhost:8181/health  # Primary OPA
curl http://localhost:8182/health  # Secondary OPA
```

## Service Endpoints

| Service | Port | Endpoint | Purpose |
|---------|------|----------|---------|
| OPA Primary | 8181 | http://localhost:8181 | Primary policy server |
| OPA Secondary | 8182 | http://localhost:8182 | Backup policy server |
| Load Balancer | 8180 | http://localhost:8180 | HA endpoint |
| Prometheus | 9090 | http://localhost:9090 | Metrics collection |
| Grafana | 3000 | http://localhost:3000 | Dashboards (admin/admin) |

## Architecture

```
┌─────────────┐
│   Clients   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Nginx LB   │ :8180
└──────┬──────┘
       │
   ┌───┴───┐
   │       │
   ▼       ▼
┌──────┐ ┌──────┐
│ OPA  │ │ OPA  │
│ :8181│ │ :8182│
└──┬───┘ └───┬──┘
   │         │
   └────┬────┘
        ▼
  ┌──────────┐
  │Prometheus│ :9090
  └────┬─────┘
       │
       ▼
  ┌─────────┐
  │ Grafana │ :3000
  └─────────┘
```

## Configuration Files

### docker-compose.yml
Complete orchestration with:
- 2 OPA instances (HA)
- Nginx load balancer
- Prometheus monitoring
- Grafana visualization

### nginx.conf
Load balancing with:
- Least connections algorithm
- Health checks
- Failover to secondary
- Performance tuning

### prometheus.yml
Metrics collection for:
- OPA instances
- Load balancer
- Policy evaluation metrics

## Deployment Steps

### 1. Pre-deployment Validation

```bash
# Validate policies
opa check .

# Run tests
opa test . -v

# Check data file
opa eval --data data.json "data"
```

### 2. Build and Start

```bash
# Pull images
docker compose pull

# Start services
docker compose up -d

# View logs
docker compose logs -f
```

### 3. Verify Deployment

```bash
# Health checks
curl http://localhost:8180/health  # Should return {"status": "ok"}
curl http://localhost:8181/health
curl http://localhost:8182/health

# Test policy query
curl -X POST http://localhost:8180/v1/data/acgs/constitutional/allow \
    -H "Content-Type: application/json" \
    -d @test_inputs/valid_message.json

# Check metrics
curl http://localhost:8181/metrics
```

### 4. Integration Testing

```bash
# Run integration tests
python3 << 'EOF'
import requests
import json

# Test constitutional validation
with open('test_inputs/valid_message.json') as f:
    data = json.load(f)

response = requests.post(
    'http://localhost:8180/v1/data/acgs/constitutional/allow',
    json=data
)

print(f"Status: {response.status_code}")
print(f"Result: {response.json()}")
assert response.json()['result'] == True, "Constitutional validation failed"
print("✅ Integration test passed")
EOF
```

## Monitoring

### Prometheus Queries

Access Prometheus at http://localhost:9090

**Policy Evaluation Latency:**
```promql
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket{job="opa-primary"}[5m]))
```

**Request Rate:**
```promql
rate(http_request_duration_seconds_count{job="opa-primary"}[1m])
```

**Error Rate:**
```promql
rate(http_request_duration_seconds_count{job="opa-primary",code=~"5.."}[1m])
```

### Grafana Dashboards

Access Grafana at http://localhost:3000 (admin/admin)

**Pre-configured Dashboards:**
1. OPA Overview - Request rates, latencies, error rates
2. Policy Performance - Per-policy evaluation metrics
3. Constitutional Compliance - Hash validation metrics
4. Authorization Metrics - RBAC decision metrics
5. Deliberation Routing - Fast lane vs deliberation statistics

## Scaling

### Horizontal Scaling

Add more OPA instances:

```yaml
# docker-compose.yml
opa-tertiary:
  image: openpolicyagent/opa:0.60.0-rootless
  container_name: acgs2-opa-tertiary
  ports:
    - "8183:8181"
  # ... same config as opa-secondary
```

Update nginx.conf:

```nginx
upstream opa_backend {
    least_conn;
    server opa-primary:8181;
    server opa-secondary:8181;
    server opa-tertiary:8181;
}
```

### Vertical Scaling

Increase resources in docker-compose.yml:

```yaml
opa-primary:
  deploy:
    resources:
      limits:
        cpus: '2'
        memory: 2G
      reservations:
        cpus: '1'
        memory: 1G
```

## Performance Tuning

### OPA Optimization

```bash
# Enable optimization level 1
--optimization=1

# Increase cache size
--set=caching.inter_query_builtin_cache.max_size_bytes=104857600

# Tune timeouts
--set=decision_logs.reporting.max_delay_seconds=10
```

### Nginx Tuning

```nginx
# nginx.conf
worker_processes auto;
worker_rlimit_nofile 65535;

events {
    worker_connections 4096;
    use epoll;
    multi_accept on;
}

http {
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    keepalive_requests 100;
}
```

## Security

### TLS/SSL Configuration

Create certificates:

```bash
# Generate self-signed certificate (development)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout opa-key.pem -out opa-cert.pem

# Update docker-compose.yml
volumes:
  - ./opa-cert.pem:/certs/cert.pem:ro
  - ./opa-key.pem:/certs/key.pem:ro

command:
  - "--tls-cert-file=/certs/cert.pem"
  - "--tls-private-key-file=/certs/key.pem"
```

### Authentication

Add authentication to nginx.conf:

```nginx
location /v1/ {
    auth_basic "OPA Policy Server";
    auth_basic_user_file /etc/nginx/.htpasswd;
    proxy_pass http://opa_backend;
}
```

Create password file:

```bash
htpasswd -c .htpasswd acgs2_user
```

## Backup and Recovery

### Policy Backup

```bash
# Backup policies
tar -czf opa-policies-$(date +%Y%m%d).tar.gz \
    constitutional/ agent_bus/ deliberation/ data.json

# Restore policies
tar -xzf opa-policies-20251217.tar.gz
docker compose restart
```

### Data Backup

```bash
# Backup Prometheus data
docker compose exec prometheus tar -czf /backup/prometheus.tar.gz /prometheus

# Backup Grafana data
docker compose exec grafana tar -czf /backup/grafana.tar.gz /var/lib/grafana
```

## Troubleshooting

### Service Not Starting

```bash
# Check logs
docker compose logs opa-primary

# Check container status
docker compose ps

# Restart service
docker compose restart opa-primary
```

### Policy Evaluation Errors

```bash
# Test policy directly
docker compose exec opa-primary opa eval \
    --data /policies/constitutional/main.rego \
    --data /policies/data.json \
    --input /policies/test_inputs/valid_message.json \
    "data.acgs.constitutional.allow"
```

### High Latency

```bash
# Check metrics
curl http://localhost:8181/metrics | grep http_request_duration

# Enable profiling
docker compose exec opa-primary opa eval \
    --profile \
    --data /policies \
    --input test.json \
    "data.acgs.constitutional.allow"
```

## Maintenance

### Update Policies

```bash
# Update policy files
# Policies are mounted as volumes and will auto-reload

# Force reload
docker compose restart opa-primary opa-secondary
```

### Update OPA Version

```bash
# Edit docker-compose.yml
image: openpolicyagent/opa:0.61.0-rootless

# Pull new image
docker compose pull

# Restart services
docker compose up -d
```

### Log Rotation

```bash
# Configure Docker log rotation
# /etc/docker/daemon.json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

## Production Checklist

- [ ] Policies validated with `opa check`
- [ ] All tests passing with `opa test`
- [ ] Constitutional hash verified: `cdd01ef066bc6cf2`
- [ ] TLS/SSL configured
- [ ] Authentication enabled
- [ ] Monitoring configured
- [ ] Alerting configured
- [ ] Backup strategy in place
- [ ] High availability deployed
- [ ] Performance tested
- [ ] Documentation updated
- [ ] Team trained

## Support

For issues or questions:
- Check logs: `docker compose logs`
- OPA Documentation: https://www.openpolicyagent.org/docs/
- ACGS-2 Documentation: `/home/dislove/document/acgs2/docs/`
- Constitutional Hash: `cdd01ef066bc6cf2`
