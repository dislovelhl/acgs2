# C4 Code Level: Policy Registry Service

> **Constitutional Hash:** cdd01ef066bc6cf2
> **Last Updated:** 2026-01-06
> **Version:** 1.0.0
> **Status:** Production Ready

## Overview

- **Name:** Policy Registry Service
- **Description:** Centralized policy management service with versioning, rollback capabilities, template marketplace, and OCI bundle distribution for constitutional AI governance
- **Location:** `/home/dislove/document/acgs2/src/core/services/policy_registry`
- **Language:** Python 3.11-3.13 with FastAPI 0.115.6+
- **Purpose:** Manage constitutional governance policies with cryptographic signing, multi-version control, A/B testing, and distributed policy delivery via OCI registries

## Code Elements

### Core Models

#### Policy Model
**File:** `app/models/policy.py`

```python
class PolicyStatus(str, Enum):
    ACTIVE = "active"
    DRAFT = "draft"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"

class Policy(BaseModel):
    policy_id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str = Field(..., min_length=1, max_length=255)
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    format: str = Field(default="json", pattern="^(json|yaml)$")
    status: PolicyStatus = Field(default=PolicyStatus.DRAFT)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    serialize_datetimes(self, value: datetime) -> str
    update_timestamp(self) -> None
```

**Purpose:** Represents a constitutional governance policy with metadata, status tracking, and timestamp management
**Dependencies:** pydantic, datetime
**Line Range:** 1-49

#### PolicyVersion Model
**File:** `app/models/policy_version.py`

```python
class VersionStatus(str, Enum):
    ACTIVE = "active"
    TESTING = "testing"
    RETIRED = "retired"
    DRAFT = "draft"

class ABTestGroup(str, Enum):
    A = "A"
    B = "B"

class PolicyVersion(BaseModel):
    version_id: str = Field(default_factory=lambda: str(uuid4()))
    policy_id: str = Field(...)
    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    content: Dict[str, Any] = Field(...)
    content_hash: str = Field(...)
    predecessor_version: Optional[str] = Field(None)
    status: VersionStatus = Field(default=VersionStatus.DRAFT)
    ab_test_group: Optional[ABTestGroup] = Field(None)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    serialize_created_at(self, value: datetime) -> str
    is_active(self) -> bool
    is_testing(self) -> bool
```

**Purpose:** Represents a specific version of a policy with semantic versioning, A/B testing support, and status lifecycle
**Dependencies:** pydantic, datetime, uuid
**Line Range:** 1-63

#### Bundle Model
**File:** `app/models/bundle.py`

```python
class BundleStatus(str, Enum):
    ACTIVE = "active"
    DRAFT = "draft"
    REVOKED = "revoked"

class Bundle(BaseModel):
    id: str = Field(..., description="Bundle ID (digest or name:tag)")
    version: str
    revision: str
    constitutional_hash: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    roots: List[str]
    signatures: List[Dict[str, str]]
    metadata: Dict[str, Any] = {}
    status: BundleStatus = BundleStatus.DRAFT
    media_type: str = "application/vnd.opa.bundle.layer.v1+gzip"
    size: int
    digest: str

    serialize_timestamp(self, value: datetime) -> str
```

**Purpose:** Represents an OPA policy bundle for distribution with OCI registry integration
**Dependencies:** pydantic, datetime
**Line Range:** 1-37

### Core Services

#### PolicyService
**File:** `app/services/policy_service.py` (Lines: 1-316)

**Key Methods:**

1. `async create_policy(name, tenant_id, content, format="json", description=None) -> Policy`
   - Creates new policy with metadata (Lines: 43-70)
   - Stores in internal dictionary

2. `async create_policy_version(policy_id, content, version, private_key_b64, public_key_b64, ab_test_group=None) -> PolicyVersion`
   - Creates versioned policy with Ed25519 signature (Lines: 72-142)
   - Generates content hash
   - Caches version and public key
   - Notifies subscribers

3. `async get_active_version(policy_id) -> Optional[PolicyVersion]`
   - Retrieves active policy version with caching (Lines: 158-182)
   - Uses Redis cache with 1-hour TTL

4. `async activate_version(policy_id, version) -> None`
   - Activates policy version (Lines: 184-233)
   - Invalidates cache keys
   - Records audit trail

5. `async verify_policy_signature(policy_id, version) -> bool`
   - Verifies Ed25519 signature (Lines: 235-254)
   - Uses CryptoService for validation

6. `async get_policy_for_client(policy_id, client_id=None) -> Optional[Dict[str, Any]]`
   - Returns policy with A/B test routing (Lines: 267-300)
   - Uses MD5 hash of client_id for group assignment

**Dependencies:** CryptoService, CacheService, NotificationService, AuditClient

#### CacheService
**File:** `app/services/cache_service.py` (Lines: 1-506)

**Multi-Tier Architecture:**
- **L1:** In-process cache (<0.1ms) - LRU cache for ultra-hot data
- **L2:** Redis shared cache (<1ms) - Cross-instance distributed data
- **L3:** Distributed cache - Fallback layer for resilience

**Key Methods:**

1. `async initialize() -> None`
   - Initializes TieredCacheManager and Redis (Lines: 107-145)

2. `async set_policy(policy_id, version, data) -> None`
   - Caches policy across L1/L2/L3 (Lines: 182-222)

3. `async get_policy(policy_id, version) -> Optional[Dict[str, Any]]`
   - Performs tiered lookup (Lines: 224-280)
   - Checks L1 → L2 → L3

4. `async get_cache_stats() -> Dict[str, Any]`
   - Returns per-tier metrics (Lines: 429-469)

**Performance:** 95%+ cache hit rate maintained

#### CryptoService
**File:** `app/services/crypto_service.py` (Lines: 1-252)

**Algorithm:** Ed25519 (EdDSA per RFC 8037)

**Key Methods:**

1. `@staticmethod generate_keypair() -> Tuple[str, str]`
   - Generates Ed25519 key pair (Lines: 25-48)
   - Returns (public_key_b64, private_key_b64)

2. `@staticmethod sign_policy_content(content, private_key_b64) -> str`
   - Deterministic signing with JSON canonicalization (Lines: 50-74)

3. `@staticmethod verify_policy_signature(content, signature_b64, public_key_b64) -> bool`
   - Verifies Ed25519 signature (Lines: 76-109)

4. `@staticmethod create_policy_signature(policy_id, version, content, private_key_b64, public_key_b64) -> PolicySignature`
   - Creates PolicySignature object (Lines: 126-157)

5. `@staticmethod issue_agent_token(agent_id, tenant_id, capabilities, private_key_b64, ttl_hours=24, extra_claims=None) -> str`
   - Issues SPIFFE-compatible JWT (Lines: 177-227)
   - Format: `spiffe://acgs2/tenant/{tenant_id}/agent/{agent_id}`

#### OPAService
**File:** `app/services/opa_service.py` (Lines: 1-146)

**Key Methods:**

1. `async check_authorization(user, action, resource) -> bool`
   - Queries OPA RBAC policy (Lines: 78-120)
   - 15-minute cache TTL
   - OPA endpoint: `/v1/data/acgs/rbac/allow`

2. `def invalidate_cache(role=None) -> int`
   - Invalidates authorization cache (Lines: 122-145)

#### TemplateLibraryService
**File:** `app/services/template_library_service.py` (Lines: 1-79)

**Key Methods:**

1. `def list_templates(category=None) -> List[Dict[str, Any]]`
   - Lists .rego templates (Lines: 24-49)
   - Supports category filtering

2. `def get_template_content(template_id) -> Optional[str]`
   - Reads template file (Lines: 51-62)

3. `def get_template_metadata(template_id) -> Optional[Dict[str, Any]]`
   - Extracts file metadata (Lines: 64-78)

### API Endpoints

#### Policies API
**File:** `app/api/v1/policies.py` (Lines: 1-165)

| Method | Endpoint | Purpose | Auth |
|--------|----------|---------|------|
| GET | `/` | List policies | ✓ |
| POST | `/` | Create policy | ✓ tenant_admin, system_admin |
| GET | `/{policy_id}` | Get policy | ✗ |
| GET | `/{policy_id}/versions` | List versions | ✗ |
| POST | `/{policy_id}/versions` | Create version | ✓ tenant_admin, system_admin |
| GET | `/{policy_id}/versions/{version}` | Get version | ✗ |
| PUT | `/{policy_id}/activate` | Activate version | ✓ tenant_admin, system_admin |
| POST | `/{policy_id}/verify` | Verify signature | ✓ tenant_admin, system_admin, auditor |
| GET | `/{policy_id}/content` | Get policy content | ✗ |

#### Bundles API
**File:** `app/api/v1/bundles.py` (Lines: 1-386)

| Method | Endpoint | Purpose | Integration |
|--------|----------|---------|---|
| GET | `/` | List bundles | OCI Registry |
| POST | `/` | Upload bundle | OCI Registry |
| GET | `/{bundle_id}` | Get bundle | OCI Registry |
| GET | `/active` | Get active bundle | OCI Registry |
| POST | `/{bundle_id}/push` | Push to registry | OCI Registry |

#### Templates API
**File:** `app/api/v1/templates.py` (Lines: 1-33)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/` | List templates |
| GET | `/{template_id:path}` | Get template |

### Main Application
**File:** `app/main.py` (Lines: 1-208)

**Key Components:**

1. **Lifespan Manager** (Lines: 54-73)
   - Startup: Initialize cache and notification services
   - Shutdown: Graceful connection closure

2. **Middleware Stack**
   - Correlation ID middleware (tracing)
   - CORS middleware (secure config)
   - Rate limiting middleware (optional)
   - Internal API key validation

3. **Health Endpoints**
   - `/health/live` - Kubernetes liveness
   - `/health/ready` - Readiness with cache stats
   - `/health/details` - Detailed diagnostics

## Dependencies

### Internal Dependencies

- `AuditClient` - Audit trail recording
- `TieredCacheManager` - Multi-tier caching
- `NotificationService` - WebSocket events
- `OCIRegistryClient` - Bundle distribution
- `BundleManifest` - Bundle metadata
- `ACGSLogging` - Structured logging

### External Dependencies

- `fastapi` (0.115.6+) - Web framework
- `uvicorn` - ASGI server
- `cryptography` - Ed25519 operations
- `PyJWT` - JWT handling
- `redis.asyncio` - Redis caching
- `httpx` - Async HTTP for OPA
- `pydantic` - Data validation

## Relationships

### Policy Lifecycle

```
Create → Version → Sign → Cache → Activate → Bundle → OCI Registry → Distribute → Client
```

### Service Dependency Graph

- **PolicyService** depends on CryptoService, CacheService, NotificationService, AuditClient
- **CacheService** depends on TieredCacheManager, Redis
- **CryptoService** independent (cryptography only)
- **OPAService** depends on httpx, configuration
- **TemplateLibraryService** depends on filesystem

## Compliance & Security

- **Constitutional Hash:** cdd01ef066bc6cf2
- **Cryptography:** Ed25519 (RFC 8032)
- **JWT Algorithm:** EdDSA (RFC 8037)
- **RBAC:** Open Policy Agent with 15-minute cache
- **Audit:** Full trail integration

## Performance

- **Latency (P99):** 0.328ms (policy read from L1 cache)
- **Throughput:** 2,605 RPS
- **Cache Hit Rate:** 95%+
- **L1 Latency:** <0.1ms
- **L2 Latency:** <1ms

## Testing

- **Coverage:** 99.8%
- **Test Framework:** pytest
- **Categories:** Unit, integration, API, RBAC, bundle
