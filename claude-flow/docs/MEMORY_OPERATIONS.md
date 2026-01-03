# Memory Operations Guide

> **Operational Procedures for Redis-Backed Persistent Memory in Claude Flow**

## Overview

This guide provides comprehensive operational procedures for managing the Redis-backed persistent memory system in the claude-flow service. The MemoryService stores governance state that must persist across sessions, pod rescheduling events, and service restarts.

## Architecture

### Components

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Claude Flow   │────▶│  MemoryService  │────▶│     Redis       │
│   CLI Service   │     │  (TypeScript)   │     │   (Persistent)  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### Key Naming Convention

All governance state keys follow the pattern:
```
governance:{tenant}:{resource_type}:{id}
```

Examples:
- `governance:acgs-dev:decision:abc123`
- `governance:acgs-dev:policy:policy-001`
- `governance:acgs-dev:session:sess-xyz`

### Environment Configuration

| Variable | Development | Production | Description |
|----------|-------------|------------|-------------|
| `REDIS_URL` | `redis://redis:6379/0` | `rediss://redis:6380/0` | Redis connection URL |
| `REDIS_PASSWORD` | (not required) | (required) | Authentication password |
| `MEMORY_DEFAULT_TTL_SECONDS` | `86400` | `86400` | Default key TTL (24 hours) |
| `MEMORY_MAX_RECONNECT_ATTEMPTS` | `10` | `10` | Max reconnection attempts |

---

## Backup Procedures

### Option 1: Manual Backup with SAVE Command

The `SAVE` command creates a synchronous point-in-time snapshot. **Use sparingly in production** as it blocks the Redis server.

```bash
# Connect to Redis CLI
# Development:
docker exec -it acgs2-core-redis-1 redis-cli

# Production (with password):
docker exec -it acgs2-core-redis-1 redis-cli -a $REDIS_PASSWORD

# Create blocking snapshot (use only if necessary)
redis-cli> SAVE
OK

# The snapshot is saved to: /data/dump.rdb (inside container)
```

### Option 2: Background Backup with BGSAVE (Recommended)

The `BGSAVE` command creates an asynchronous snapshot without blocking.

```bash
# Trigger background save
redis-cli> BGSAVE
Background saving started

# Check save status
redis-cli> LASTSAVE
(integer) 1704240000

# Monitor save progress
redis-cli> INFO persistence
# Look for: rdb_bgsave_in_progress:0 (0 = complete)
```

### Option 3: Automated Backup Script

Create a backup script for regular scheduled backups:

```bash
#!/bin/bash
# backup_redis.sh - Redis backup script for governance memory

BACKUP_DIR="/var/backups/redis"
REDIS_CONTAINER="acgs2-core-redis-1"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/dump_${TIMESTAMP}.rdb"

# Create backup directory
mkdir -p $BACKUP_DIR

# Trigger background save
docker exec $REDIS_CONTAINER redis-cli BGSAVE

# Wait for save to complete (max 60 seconds)
for i in {1..60}; do
    STATUS=$(docker exec $REDIS_CONTAINER redis-cli INFO persistence | grep rdb_bgsave_in_progress:0)
    if [ -n "$STATUS" ]; then
        break
    fi
    sleep 1
done

# Copy dump file from container
docker cp $REDIS_CONTAINER:/data/dump.rdb $BACKUP_FILE

# Verify backup
if [ -f "$BACKUP_FILE" ] && [ -s "$BACKUP_FILE" ]; then
    echo "Backup successful: $BACKUP_FILE"
    # Keep only last 7 backups
    ls -tp ${BACKUP_DIR}/dump_*.rdb | tail -n +8 | xargs -I {} rm -- {}
else
    echo "ERROR: Backup failed!"
    exit 1
fi
```

### Option 4: Scheduled Backups with Cron

```bash
# Add to crontab (crontab -e)
# Daily backup at 2 AM
0 2 * * * /path/to/backup_redis.sh >> /var/log/redis_backup.log 2>&1

# Hourly backup for critical environments
0 * * * * /path/to/backup_redis.sh >> /var/log/redis_backup.log 2>&1
```

---

## Restore Procedures

### Restore from RDB File

**IMPORTANT**: Restoring replaces all current data. Ensure you have a backup of the current state if needed.

#### Step 1: Stop Claude Flow Service

```bash
# Stop the service to prevent writes during restore
docker-compose -f docker-compose.dev.yml stop claude-flow

# Or for production:
kubectl scale deployment claude-flow --replicas=0
```

#### Step 2: Stop Redis Server

```bash
# Development
docker-compose -f docker-compose.dev.yml stop redis

# Production (Kubernetes)
kubectl scale statefulset redis --replicas=0
```

#### Step 3: Replace RDB File

```bash
# Copy backup file to Redis data directory
docker cp /path/to/backup/dump.rdb acgs2-core-redis-1:/data/dump.rdb

# Or if Redis is stopped:
cp /path/to/backup/dump.rdb /var/lib/redis/dump.rdb
```

#### Step 4: Start Redis Server

```bash
# Development
docker-compose -f docker-compose.dev.yml start redis

# Wait for Redis to load RDB file
sleep 5

# Verify data loaded
docker exec acgs2-core-redis-1 redis-cli DBSIZE
```

#### Step 5: Verify Restoration

```bash
# Check key count
redis-cli> DBSIZE
(integer) 1234

# List governance keys
redis-cli> SCAN 0 MATCH governance:* COUNT 100

# Spot check specific keys
redis-cli> GET governance:acgs-dev:decision:sample-id
```

#### Step 6: Restart Claude Flow Service

```bash
# Development
docker-compose -f docker-compose.dev.yml start claude-flow

# Production (Kubernetes)
kubectl scale deployment claude-flow --replicas=1
```

---

## Redis Persistence Configuration

### RDB (Snapshotting) Configuration

Add to `redis.conf` for automatic snapshots:

```conf
# Save snapshot if at least 1 key changed in 900 seconds
save 900 1

# Save snapshot if at least 10 keys changed in 300 seconds
save 300 10

# Save snapshot if at least 10000 keys changed in 60 seconds
save 60 10000

# Stop accepting writes if RDB save fails
stop-writes-on-bgsave-error yes

# Compress RDB files
rdbcompression yes

# Verify RDB checksum on load
rdbchecksum yes

# RDB filename
dbfilename dump.rdb

# Working directory for RDB file
dir /data
```

### AOF (Append-Only File) Configuration (Optional)

For higher durability, enable AOF alongside RDB:

```conf
# Enable AOF persistence
appendonly yes

# AOF filename
appendfilename "appendonly.aof"

# Fsync policy: everysec provides good balance
# Options: always (safest), everysec (recommended), no (fastest)
appendfsync everysec

# Rewrite AOF when it grows too large
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb
```

### Memory Policy Configuration

Configure eviction policy for memory limits:

```conf
# Maximum memory limit
maxmemory 256mb

# Eviction policy: remove least recently used keys first
# Recommended for governance data: allkeys-lru
maxmemory-policy allkeys-lru

# Sample size for LRU algorithm
maxmemory-samples 5
```

---

## Troubleshooting Connection Issues

### Issue: Cannot Connect to Redis

**Symptoms**:
- MemoryService logs: "Failed to connect to Redis"
- Connection state: "error"

**Diagnosis**:

```bash
# 1. Check if Redis container is running
docker ps | grep redis

# 2. Test network connectivity
docker exec claude-flow ping redis
# Or:
nc -zv redis 6379

# 3. Test Redis connection directly
docker exec acgs2-core-redis-1 redis-cli ping
# Expected: PONG

# 4. Check Redis logs
docker logs acgs2-core-redis-1 --tail 50
```

**Solutions**:

| Problem | Solution |
|---------|----------|
| Container not running | `docker-compose up -d redis` |
| Wrong REDIS_URL | Verify URL matches docker-compose service name |
| Port not exposed | Check docker-compose.yml ports mapping |
| Network issues | Ensure services are on same Docker network |

### Issue: Authentication Failed

**Symptoms**:
- MemoryService logs: "NOAUTH Authentication required"
- Production only (dev has no password)

**Diagnosis**:

```bash
# Test with password
docker exec acgs2-core-redis-1 redis-cli -a "$REDIS_PASSWORD" ping
```

**Solutions**:

| Problem | Solution |
|---------|----------|
| Missing REDIS_PASSWORD env var | Add to environment/secrets |
| Wrong password | Verify password matches Redis config |
| Password contains special chars | URL-encode the password |

### Issue: Connection Keeps Dropping

**Symptoms**:
- MemoryService logs: "Redis reconnecting..."
- Frequent state changes: connected -> error -> reconnecting

**Diagnosis**:

```bash
# 1. Check Redis memory usage
redis-cli> INFO memory
# Look for: used_memory_human, maxmemory

# 2. Check client connections
redis-cli> CLIENT LIST

# 3. Check for timeouts
redis-cli> CONFIG GET timeout
```

**Solutions**:

| Problem | Solution |
|---------|----------|
| Memory exhaustion | Increase maxmemory or enable eviction |
| Too many connections | Implement connection pooling (already done) |
| Network instability | Check container networking, increase reconnect attempts |
| Timeout too low | Increase client timeout in Redis config |

### Issue: TLS Connection Fails (Production)

**Symptoms**:
- MemoryService logs: "TLS handshake failed"
- Only affects rediss:// URLs

**Diagnosis**:

```bash
# Test TLS connection
openssl s_client -connect redis:6380

# Check certificate
openssl s_client -connect redis:6380 -showcerts
```

**Solutions**:

| Problem | Solution |
|---------|----------|
| Certificate expired | Renew TLS certificate |
| Self-signed cert rejected | Set `rejectUnauthorized: false` (already configured) |
| Wrong TLS port | Verify using port 6380 for TLS |
| Missing TLS config | Ensure REDIS_URL starts with `rediss://` |

### Issue: Slow Operations (Latency > 10ms)

**Symptoms**:
- MemoryService health shows high latency
- Operations taking longer than expected

**Diagnosis**:

```bash
# 1. Check Redis latency
redis-cli> DEBUG SLEEP 0
redis-cli> SLOWLOG GET 10

# 2. Check if KEYS command is being used (should not be)
redis-cli> SLOWLOG GET 100 | grep KEYS

# 3. Monitor real-time commands
redis-cli> MONITOR
# Press Ctrl+C to stop
```

**Solutions**:

| Problem | Solution |
|---------|----------|
| KEYS command used | Use SCAN instead (already implemented) |
| Large values | Keep values under 1KB |
| Network latency | Move Redis closer to application |
| Too many clients | Review connection pooling |

---

## Disaster Recovery Runbook

### Scenario 1: Redis Data Loss

**Severity**: Critical
**RTO**: 30 minutes
**RPO**: Depends on backup frequency

**Steps**:

1. **Assess damage**
   ```bash
   redis-cli> DBSIZE
   # If 0 or missing governance keys, proceed with recovery
   ```

2. **Stop all services writing to Redis**
   ```bash
   kubectl scale deployment claude-flow --replicas=0
   ```

3. **Locate latest backup**
   ```bash
   ls -lt /var/backups/redis/dump_*.rdb | head -5
   ```

4. **Restore from backup** (follow Restore Procedures above)

5. **Verify data integrity**
   ```bash
   redis-cli> SCAN 0 MATCH governance:* COUNT 100
   ```

6. **Restart services**
   ```bash
   kubectl scale deployment claude-flow --replicas=1
   ```

7. **Monitor for issues**
   ```bash
   kubectl logs -f deployment/claude-flow
   ```

### Scenario 2: Redis Server Failure

**Severity**: High
**RTO**: 15 minutes

**Steps**:

1. **Identify failure**
   ```bash
   docker ps | grep redis
   docker logs acgs2-core-redis-1 --tail 100
   ```

2. **Attempt restart**
   ```bash
   docker-compose -f docker-compose.dev.yml restart redis
   ```

3. **If restart fails, recreate container**
   ```bash
   docker-compose -f docker-compose.dev.yml down redis
   docker-compose -f docker-compose.dev.yml up -d redis
   ```

4. **Verify data persisted**
   ```bash
   redis-cli> DBSIZE
   redis-cli> SCAN 0 MATCH governance:* COUNT 10
   ```

5. **Check Claude Flow reconnection**
   ```bash
   # Service should auto-reconnect within 10 attempts
   docker logs claude-flow --tail 50 | grep -i redis
   ```

### Scenario 3: Network Partition

**Severity**: Medium
**RTO**: 5 minutes (auto-recovery)

**Steps**:

1. **Wait for auto-reconnection**
   - MemoryService has exponential backoff
   - Max 10 attempts with 50-500ms delays

2. **If auto-recovery fails**
   ```bash
   # Restart Claude Flow to force reconnection
   kubectl rollout restart deployment/claude-flow
   ```

3. **Check network**
   ```bash
   kubectl exec -it claude-flow-pod -- ping redis
   kubectl exec -it claude-flow-pod -- nc -zv redis 6379
   ```

### Scenario 4: Corrupted Data

**Severity**: High
**RTO**: 45 minutes

**Steps**:

1. **Identify corrupted keys**
   ```bash
   # MemoryService logs malformed JSON warnings
   kubectl logs deployment/claude-flow | grep "Malformed JSON"
   ```

2. **Delete corrupted keys**
   ```bash
   redis-cli> DEL governance:acgs-dev:corrupted-key
   ```

3. **If widespread corruption**
   - Stop services
   - Restore from last known good backup
   - Verify data integrity
   - Restart services

4. **Investigate root cause**
   - Check for encoding issues
   - Review recent code changes
   - Check for incomplete writes

---

## Monitoring and Alerting

### Key Metrics to Monitor

| Metric | Warning Threshold | Critical Threshold |
|--------|------------------|-------------------|
| Connection State | `reconnecting` | `error` for >30s |
| Latency (PING) | >5ms | >10ms |
| Memory Usage | >80% maxmemory | >95% maxmemory |
| Reconnect Attempts | >3 | >8 |
| Keys Count | Sudden drop >50% | Drop to 0 |

### Health Check Command

```bash
# Get MemoryService health status
curl -s http://localhost:3000/health/memory | jq .

# Expected healthy response:
# {
#   "healthy": true,
#   "connectionState": "connected",
#   "reconnectAttempts": 0,
#   "latencyMs": 1
# }
```

### Redis INFO Command Reference

```bash
redis-cli> INFO

# Key sections:
# - Server: version, uptime
# - Clients: connected clients, blocked clients
# - Memory: used_memory, maxmemory
# - Persistence: rdb_last_save_time, aof_enabled
# - Stats: total_connections, expired_keys
# - Replication: role, connected_slaves
```

---

## Command Reference

### MemoryService CLI Operations

```typescript
import { getMemoryService } from './services/memory';

// Initialize
const memory = getMemoryService();
await memory.initialize();

// Store with TTL
await memory.set('governance:acgs-dev:decision:123', { result: 'approved' }, { ttlSeconds: 3600 });

// Retrieve
const result = await memory.get('governance:acgs-dev:decision:123');

// Delete
await memory.delete('governance:acgs-dev:decision:123');

// Cleanup by pattern
await memory.cleanup('governance:acgs-dev:session:*');

// Health check
const health = await memory.getHealth();

// Disconnect
await memory.disconnect();
```

### Redis CLI Operations

```bash
# Connection
redis-cli                    # Connect to localhost:6379
redis-cli -h redis -p 6379   # Connect to specific host/port
redis-cli -a password        # Connect with password

# Key operations
GET key                      # Get value
SET key value               # Set value
SET key value EX 3600       # Set with TTL (seconds)
DEL key                     # Delete key
EXISTS key                  # Check if key exists
TTL key                     # Get remaining TTL
EXPIRE key seconds          # Set TTL on existing key

# Scanning (non-blocking)
SCAN 0 MATCH pattern COUNT 100

# Persistence
SAVE                        # Blocking save
BGSAVE                      # Background save
LASTSAVE                    # Last save timestamp

# Monitoring
INFO                        # Server info
CLIENT LIST                 # Connected clients
SLOWLOG GET 10              # Slow query log
DEBUG SLEEP 0               # Latency test
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | January 2026 | Initial documentation |

---

**Claude Flow Memory Operations Guide v1.0.0**
*Last Updated: January 2026*

**Maintainer**: ACGS-2 Development Team

---

*This guide ensures reliable operation of the Redis-backed persistent memory system for governance state management.*
