# Claude Flow Memory Operations Guide

This document provides operational procedures for the Redis-backed persistent memory system in claude-flow.

## Overview

The memory service provides persistent storage for governance state, enabling:
- State persistence across service restarts
- Adaptive governance through historical decision tracking
- Session continuity during pod rescheduling

## Architecture

```
┌─────────────────┐     ┌─────────────────┐
│   claude-flow   │────▶│      Redis      │
│  Memory Service │     │   (Persistent)  │
└─────────────────┘     └─────────────────┘
        │
        ▼
  ┌─────────────┐
  │   Storage   │
  │  - State    │
  │  - Sessions │
  │  - Cache    │
  └─────────────┘
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379` |
| `REDIS_PASSWORD` | Redis authentication password | (none) |
| `MEMORY_DEFAULT_TTL_SECONDS` | Default entry TTL in seconds | `86400` (24 hours) |
| `MEMORY_MAX_RECONNECT_ATTEMPTS` | Max reconnection attempts | `10` |

### Development Environment

```bash
# Use docker-compose for Redis
docker-compose -f docker-compose.dev.yml up -d redis

# Set environment
export REDIS_URL=redis://localhost:6379
```

### Production Environment

```bash
# Use TLS-enabled Redis
export REDIS_URL=rediss://redis:6380
export REDIS_PASSWORD=<secure-password>
```

## Backup Procedures

### Manual Backup (SAVE Command)

```bash
# Connect to Redis container
docker exec -it <redis-container> redis-cli

# Trigger synchronous save
SAVE

# Or use background save (non-blocking)
BGSAVE

# Check save status
LASTSAVE
```

### Automated RDB Snapshots

Configure Redis for automatic snapshots in `redis.conf`:

```conf
# Save every 900 seconds if at least 1 key changed
save 900 1

# Save every 300 seconds if at least 10 keys changed
save 300 10

# Save every 60 seconds if at least 10000 keys changed
save 60 10000
```

### Backup Location

RDB snapshots are stored at:
- Docker: `/data/dump.rdb` (inside container)
- Production: Configure via `dir` in redis.conf

## Restore Procedures

### Restore from RDB File

1. **Stop Redis service**
   ```bash
   docker stop <redis-container>
   ```

2. **Replace dump.rdb**
   ```bash
   cp backup/dump.rdb /path/to/redis/data/dump.rdb
   ```

3. **Start Redis service**
   ```bash
   docker start <redis-container>
   ```

4. **Verify restoration**
   ```bash
   docker exec -it <redis-container> redis-cli KEYS "*"
   ```

### Point-in-Time Recovery

For production environments, consider using Redis Enterprise or managed Redis services with automatic point-in-time recovery.

## Troubleshooting

### Connection Issues

**Symptom**: "Redis client not initialized" error

**Solutions**:
1. Verify Redis is running: `docker ps | grep redis`
2. Check connection URL: `redis-cli -u $REDIS_URL ping`
3. Verify network connectivity: `telnet redis-host 6379`

### Memory Pressure

**Symptom**: Redis running out of memory

**Solutions**:
1. Configure maxmemory policy:
   ```bash
   redis-cli CONFIG SET maxmemory 1gb
   redis-cli CONFIG SET maxmemory-policy allkeys-lru
   ```
2. Run cleanup for stale keys:
   ```typescript
   await memoryService.cleanup('stale:*');
   ```

### Slow Performance

**Symptom**: Memory operations taking >10ms

**Solutions**:
1. Enable connection pooling (single client instance)
2. Use SCAN instead of KEYS for iteration
3. Monitor latency: `redis-cli --latency-history`

### Authentication Failures

**Symptom**: "NOAUTH Authentication required" error

**Solutions**:
1. Verify REDIS_PASSWORD is set correctly
2. Check Redis ACL configuration
3. For development, ensure no password required

## Monitoring

### Key Metrics

| Metric | Command | Expected |
|--------|---------|----------|
| Memory usage | `INFO memory` | < 80% of maxmemory |
| Connected clients | `INFO clients` | Stable, < max clients |
| Keys count | `DBSIZE` | Consistent growth |
| Ops/second | `INFO stats` | Matches workload |

### Health Check

```bash
# Quick health check
redis-cli PING
# Expected: PONG

# Memory usage
redis-cli INFO memory | grep used_memory_human

# Key count
redis-cli DBSIZE
```

## Security

### Best Practices

1. **Never commit passwords** - Use environment variables
2. **Enable TLS in production** - Use `rediss://` URLs
3. **Configure authentication** - Set `requirepass` in redis.conf
4. **Limit network access** - Use private networks/firewalls
5. **Regular backups** - Enable RDB snapshots

### Key Naming Conventions

```
claude-flow:memory:{tenant}:{type}:{id}

Examples:
- claude-flow:memory:acgs-dev:governance:state
- claude-flow:memory:acgs-dev:agent:agent-123
- claude-flow:memory:acgs-dev:swarm:swarm-456
```

## API Reference

### Initialize Memory Service

```typescript
import { getMemoryService } from './services/memory';

const memory = getMemoryService();
await memory.initialize();
```

### Store Value

```typescript
// Store with default TTL (24 hours)
await memory.set('key', { data: 'value' });

// Store with custom TTL (1 hour)
await memory.set('key', { data: 'value' }, 3600);
```

### Retrieve Value

```typescript
const value = await memory.get<MyType>('key');
```

### Delete Value

```typescript
const deleted = await memory.delete('key');
```

### Cleanup by Pattern

```typescript
const count = await memory.cleanup('stale:*');
console.log(`Deleted ${count} stale entries`);
```

### Graceful Shutdown

```typescript
process.on('SIGTERM', async () => {
  await memory.disconnect();
  process.exit(0);
});
```
