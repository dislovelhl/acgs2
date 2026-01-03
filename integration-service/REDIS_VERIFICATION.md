# Redis Job Tracking Verification

This document describes how to verify that Redis job tracking works correctly for the import feature.

## Prerequisites

1. **Redis must be running**:
   ```bash
   docker run -d -p 6379:6379 redis:alpine
   # Or if already running:
   docker ps | grep redis
   ```

2. **Integration service must be running**:
   ```bash
   cd integration-service
   uvicorn src.main:app --reload --port 8100
   ```

## Automated Verification

Run the verification script:

```bash
cd integration-service
python3 verify_redis_job_tracking.py
```

This script will:
- ✓ Connect to Redis
- ✓ Create an import job via API
- ✓ Verify job is stored in Redis
- ✓ Validate JSON structure and required fields
- ✓ Check TTL is set correctly (24 hours)
- ✓ Retrieve job via API and verify data matches

## Manual Verification

If you prefer to verify manually, follow these steps:

### Step 1: Create an Import Job

```bash
# Create a test import job
curl -X POST http://localhost:8100/api/imports \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "jira",
    "source_config": {
      "base_url": "https://test.atlassian.net",
      "email": "test@example.com",
      "api_token": "test-token",
      "project_key": "TEST"
    },
    "options": {
      "batch_size": 100,
      "preview_limit": 10
    }
  }'
```

**Expected Response:**
```json
{
  "job_id": "12345678-1234-1234-1234-123456789abc",
  "request_id": "...",
  "status": "pending",
  "source_type": "jira",
  "created_at": "2024-01-03T...",
  "updated_at": "2024-01-03T...",
  ...
}
```

Copy the `job_id` from the response for the next steps.

### Step 2: Check Redis for Job Data

```bash
# Replace {job_id} with the actual job ID from Step 1
redis-cli GET "import:job:{job_id}"
```

**Expected Output:**
- A JSON string containing the job data
- Must include fields: `job_id`, `request_id`, `status`, `source_type`, `created_at`, `updated_at`
- Status should be `"pending"`

**Example:**
```json
{
  "job_id": "12345678-1234-1234-1234-123456789abc",
  "request_id": "abc-123",
  "status": "pending",
  "source_type": "jira",
  "created_at": "2024-01-03T10:30:00Z",
  "updated_at": "2024-01-03T10:30:00Z",
  "tenant_id": null,
  "correlation_id": null,
  "progress": null,
  "error": null,
  "started_at": null,
  "completed_at": null
}
```

### Step 3: Check TTL (Time To Live)

```bash
# Check TTL for the job key
redis-cli TTL "import:job:{job_id}"
```

**Expected Output:**
- A positive number (seconds remaining until expiration)
- Should be close to 86400 (24 hours = 86400 seconds)
- Example: `86395` (means ~24 hours minus a few seconds)

**Failure Cases:**
- `-1`: TTL not set (key will never expire) ❌
- `-2`: Key does not exist ❌
- `0` or negative: Key expired or will expire immediately ❌

### Step 4: Retrieve Job via API

```bash
# Verify the job can be retrieved via API
curl http://localhost:8100/api/imports/{job_id}
```

**Expected Response:**
- HTTP 200 OK
- JSON object with same data as created in Step 1
- `job_id` matches the one from Step 1

### Step 5: List All Jobs

```bash
# List all import jobs
curl http://localhost:8100/api/imports
```

**Expected Response:**
- HTTP 200 OK
- Array containing the job(s) you created
- Pagination info (total, limit, offset)

## Verification Checklist

- [ ] Redis is running and accessible
- [ ] Integration service is running on port 8100
- [ ] Import job can be created via POST /api/imports
- [ ] Job is stored in Redis with key `import:job:{job_id}`
- [ ] Redis value is valid JSON
- [ ] JSON contains all required fields (job_id, status, source_type, etc.)
- [ ] TTL is set to 86400 seconds (24 hours)
- [ ] Job can be retrieved via GET /api/imports/{job_id}
- [ ] Retrieved job data matches what was stored
- [ ] Jobs can be listed via GET /api/imports

## Implementation Details

### Redis Key Format

```
import:job:{job_id}
```

Example: `import:job:12345678-1234-1234-1234-123456789abc`

### TTL Configuration

- **TTL**: 86400 seconds (24 hours)
- **Purpose**: Automatic cleanup of old job data
- **Location**: Defined in `src/api/import_router.py` as `REDIS_JOB_TTL`

### Data Format

Jobs are stored as JSON strings with the following structure:

```json
{
  "job_id": "uuid",
  "request_id": "uuid",
  "status": "pending|processing|completed|failed|cancelled",
  "source_type": "jira|servicenow|github|gitlab",
  "created_at": "ISO-8601 datetime",
  "updated_at": "ISO-8601 datetime",
  "tenant_id": "string|null",
  "correlation_id": "string|null",
  "progress": {
    "total_items": 0,
    "processed_items": 0,
    "failed_items": 0,
    "percentage": 0.0
  } | null,
  "error": "string|null",
  "started_at": "ISO-8601 datetime|null",
  "completed_at": "ISO-8601 datetime|null"
}
```

## Troubleshooting

### Redis Connection Failed

**Error**: `Redis connection failed: Connection refused`

**Solution**:
```bash
# Start Redis with Docker
docker run -d -p 6379:6379 redis:alpine

# Or check if Redis is already running
docker ps | grep redis
```

### Job Not Found in Redis

**Error**: `Job not found in Redis`

**Possible Causes**:
1. Redis client not initialized (check service logs)
2. Job creation failed silently
3. Wrong Redis database selected (should be db 0)

**Solution**:
- Check integration-service logs for Redis connection errors
- Verify `REDIS_URL` environment variable: `redis://localhost:6379/0`
- Restart integration-service

### TTL Not Set

**Error**: `redis-cli TTL` returns `-1`

**Possible Causes**:
1. `ex` parameter not passed to Redis SET command
2. Redis version doesn't support TTL

**Solution**:
- Verify `save_job_to_redis()` uses `ex=REDIS_JOB_TTL`
- Check Redis version: `redis-cli INFO server | grep redis_version`
- Should be Redis 2.6.12 or higher

## Success Criteria

✅ All verification steps pass
✅ Jobs are stored in Redis with proper JSON format
✅ TTL is set to 86400 seconds
✅ Jobs can be retrieved via API
✅ Job data is consistent between Redis and API

## Related Files

- `src/api/import_router.py` - Import endpoints with Redis integration
- `src/main.py` - Redis client initialization
- `verify_redis_job_tracking.py` - Automated verification script
