# ACGS-2 Workspace Rules — Security & Performance

## Security practices

### Secrets detection

Pre-commit hooks automatically detect and block:

- API keys (Anthropic, OpenAI, AWS, etc.)
- JWT secrets and tokens
- Database credentials
- Private keys

Safe placeholder patterns: `dev-*`, `test-*`, `your-*-here`

### Zero-trust patterns

```python
from src.core.shared.security.auth import verify_jwt_token
from src.core.shared.security.rate_limiter import RateLimiter
from src.core.shared.security.tenant_context import get_tenant_context

@router.get("/protected")
async def protected_endpoint(
    token: str = Depends(verify_jwt_token),
    tenant: TenantContext = Depends(get_tenant_context),
):
    if not tenant.has_permission("read:policies"):
        raise HTTPException(status_code=403)
```

### Input validation

```python
from pydantic import BaseModel, Field, validator

class SecureInput(BaseModel):
    query: str = Field(..., max_length=1000)

    @validator("query")
    def sanitize_query(cls, v: str) -> str:
        dangerous_chars = ["'", '"', ";", "--", "/*", "*/"]
        for char in dangerous_chars:
            v = v.replace(char, "")
        return v
```

## Performance guidelines

### Target metrics

| Metric         | Target     | Current   |
| -------------- | ---------- | --------- |
| P99 Latency    | <0.5ms     | 0.328ms   |
| Throughput     | >2,000 RPS | 2,605 RPS |
| Memory/pod     | <4MB       | <4MB      |
| Cache Hit Rate | >85%       | 95%+      |

### Caching pattern

```python
from src.core.shared.tiered_cache import TieredCache

cache = TieredCache(redis_url="redis://localhost:6379")

async def get_policy(policy_id: PolicyID) -> PolicyData:
    cached = await cache.get(f"policy:{policy_id}")
    if cached:
        return cached

    policy = await db.fetch_policy(policy_id)
    await cache.set(f"policy:{policy_id}", policy, ttl=300)
    return policy
```
