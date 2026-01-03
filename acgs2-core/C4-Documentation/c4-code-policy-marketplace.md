# C4 Code Level: Policy Marketplace Service

<!-- Constitutional Hash: cdd01ef066bc6cf2 -->

## Overview

- **Name**: Policy Marketplace Service
- **Description**: FastAPI-based marketplace for sharing, rating, and distributing governance policies with community review workflows and comprehensive analytics
- **Location**: `/acgs2-core/services/policy_marketplace/`
- **Language**: Python 3.11+
- **Framework**: FastAPI 0.115.6+, SQLAlchemy 2.0
- **Port**: 8003
- **Purpose**: Provide a community-driven marketplace for policy templates with version control, peer review, and usage analytics integrated with the ACGS constitutional governance framework

## Architecture Overview

The Policy Marketplace Service implements a modular, layered architecture following FastAPI best practices:

```
┌─────────────────────────────────────────────────────┐
│              FastAPI Application (main.py)          │
│  - CORS & Rate Limiting Middleware                  │
│  - Internal Auth Middleware                         │
│  - Health Check Endpoints                           │
└─────────────────────────────────┬───────────────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
        ┌───────────▼──────────┐   ┌──────────▼────────┐
        │  API Layer (v1)      │   │  Database Layer   │
        │  ├── templates       │   │  ├── models       │
        │  ├── versions        │   │  ├── schemas      │
        │  ├── reviews         │   │  └── settings     │
        │  └── analytics       │   └───────────────────┘
        └──────────────────────┘
```

## Code Elements

### Application Initialization

#### `main.py` - FastAPI Application Factory

**Location**: `/app/main.py`

**Purpose**: Initializes FastAPI application with middleware, routers, and health checks

**Key Components**:

- **FastAPI App**: `app = FastAPI(title="Policy Marketplace Service", ...)`
  - Main application instance serving on port 8003
  - Lifespan context manager for startup/shutdown events
  - Global exception handler for unhandled errors

- **CORS Middleware**: Configurable CORS with secure defaults
  - Uses `shared.security.cors_config` if available
  - Fallback to settings-based configuration
  - Allowed methods: GET, POST, PUT, DELETE, PATCH, OPTIONS
  - Required headers: Authorization, Content-Type, X-Request-ID

- **Rate Limiting Middleware**: Optional rate limiting with configuration
  - Uses `shared.security.rate_limiter` if available
  - Configurable rules via RateLimitConfig

- **Internal Auth Middleware**:
  - `internal_auth_middleware(request, call_next): Middleware`
  - Validates `X-Internal-API-Key` header for `/api/v1` routes
  - Returns 401 Unauthorized for invalid keys

- **Health Check Endpoints**:
  - `GET /health/live`: Liveness probe for Kubernetes
  - `GET /health/ready`: Readiness probe for Kubernetes
  - `GET /health/details`: Detailed health information

- **Router Registration**:
  - `router.include_router(v1_router, prefix="/api/v1")`
  - Routes all v1 API endpoints under `/api/v1`

---

### Database Layer

#### `database.py` - Async Database Configuration

**Location**: `/app/database.py`

**Purpose**: Manages SQLAlchemy async database connections and sessions

**Functions**:

- `create_async_engine(database_url, pool_pre_ping=True, echo=settings.debug) -> AsyncEngine`
  - Creates async SQLAlchemy engine for PostgreSQL
  - Connection pooling with pre-ping for stale connections
  - Debug logging configurable via settings

- `AsyncSessionLocal = sessionmaker(..., class_=AsyncSession)`
  - Session factory for creating async database sessions
  - Configured for automatic cleanup

- `async get_db() -> AsyncGenerator[AsyncSession, None]`
  - Dependency injection function for FastAPI routes
  - Returns async session with transaction management
  - Automatically commits on success, rolls back on error
  - Always closes session in finally block

**Dependencies**:
- SQLAlchemy 2.0+ (asyncpg driver)
- PostgreSQL database
- Settings configuration for database_url

---

#### `models/base.py` - SQLAlchemy Base Class

**Location**: `/app/models/base.py`

**Purpose**: Provides declarative base for all SQLAlchemy ORM models

**Classes**:

- `Base(DeclarativeBase)`
  - SQLAlchemy 2.0 declarative base class
  - All models inherit from this class
  - Provides metadata and table registration

---

#### `models/template.py` - Database Models

**Location**: `/app/models/template.py`

**Purpose**: Defines SQLAlchemy ORM models for templates, versions, ratings, and analytics

**Enumerations**:

- `TemplateStatus(str, Enum)`: Template lifecycle status
  - Values: `DRAFT`, `PENDING_REVIEW`, `PUBLISHED`, `REJECTED`, `ARCHIVED`
  - Used for review workflow and visibility control

- `TemplateFormat(str, Enum)`: Supported policy template formats
  - Values: `JSON`, `YAML`, `REGO`
  - Determines file format validation and parsing

- `TemplateCategory(str, Enum)`: Policy template categories
  - Values: `COMPLIANCE`, `ACCESS_CONTROL`, `DATA_PROTECTION`, `AUDIT`, `RATE_LIMITING`, `MULTI_TENANT`, `API_SECURITY`, `DATA_RETENTION`, `CUSTOM`
  - Enables organization and filtering

**Classes**:

##### `Template` (ORM Model)

**Table**: `templates`

**Columns**:

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| `id` | Integer | PRIMARY KEY, AUTO INCREMENT | Unique template identifier |
| `name` | String(255) | NOT NULL | Template name |
| `description` | Text | NOT NULL | Detailed template description |
| `content` | Text | NOT NULL | Policy template content (JSON/YAML/Rego) |
| `category` | String(100) | NOT NULL, INDEX | Template category for filtering |
| `format` | String(20) | NOT NULL, DEFAULT='json' | File format (json, yaml, rego) |
| `status` | String(50) | NOT NULL, DEFAULT='draft', INDEX | Workflow status (draft, pending_review, published, rejected, archived) |
| `is_verified` | Boolean | NOT NULL, DEFAULT=False, INDEX | Whether template passed verification |
| `is_public` | Boolean | NOT NULL, DEFAULT=True, INDEX | Public/private visibility flag |
| `organization_id` | String(100) | NULLABLE, INDEX | Organization ID for private templates |
| `author_id` | String(100) | NULLABLE | User ID of template creator |
| `author_name` | String(255) | NULLABLE | Display name of template creator |
| `current_version` | String(20) | NOT NULL, DEFAULT='1.0.0' | Semantic version (major.minor.patch) |
| `downloads` | Integer | NOT NULL, DEFAULT=0 | Total download count for analytics |
| `rating` | Float | NULLABLE | Average rating (1.0-5.0) |
| `rating_count` | Integer | NOT NULL, DEFAULT=0 | Number of ratings submitted |
| `is_deleted` | Boolean | NOT NULL, DEFAULT=False, INDEX | Soft delete flag |
| `created_at` | DateTime(tz=True) | NOT NULL, DEFAULT=now(), INDEX | Creation timestamp |
| `updated_at` | DateTime(tz=True) | NOT NULL, DEFAULT=now(), ONUPDATE=now() | Last modification timestamp |

**Relationships**:

- `versions: Mapped[list[TemplateVersion]]`
  - One-to-many relationship to TemplateVersion
  - Cascade delete orphans
  - Enables version history tracking

- `ratings: Mapped[list[TemplateRating]]`
  - One-to-many relationship to TemplateRating
  - Cascade delete orphans
  - Enables community feedback collection

**Indexes**:

- Composite indexes for common query patterns
- Performance optimization for filtering and sorting
- Unique constraint on (name, organization_id) for template deduplication

**Methods**:

- `__repr__() -> str`: Returns string representation with id, name, category

---

##### `TemplateVersion` (ORM Model)

**Table**: `template_versions`

**Purpose**: Maintains complete version history for template content changes

**Columns**:

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| `id` | Integer | PRIMARY KEY, AUTO INCREMENT | Unique version identifier |
| `template_id` | Integer | FOREIGN KEY → templates.id (CASCADE) | Parent template reference |
| `version` | String(20) | NOT NULL | Semantic version identifier |
| `content` | Text | NOT NULL | Full template content at this version |
| `content_hash` | String(64) | NOT NULL | SHA-256 hash for integrity verification |
| `changelog` | Text | NULLABLE | Release notes/changelog for this version |
| `created_by` | String(100) | NULLABLE | User ID who created this version |
| `created_at` | DateTime(tz=True) | NOT NULL, DEFAULT=now() | Version creation timestamp |

**Relationships**:

- `template: Mapped[Template]`
  - Many-to-one relationship back to Template
  - Provides access to parent template

**Constraints**:

- Unique constraint on (template_id, version) to prevent duplicate versions
- Cascade delete when parent template is deleted

**Methods**:

- `__repr__() -> str`: Returns version info with template_id and version

---

##### `TemplateRating` (ORM Model)

**Table**: `template_ratings`

**Purpose**: Stores community ratings and reviews for templates

**Columns**:

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| `id` | Integer | PRIMARY KEY, AUTO INCREMENT | Unique rating identifier |
| `template_id` | Integer | FOREIGN KEY → templates.id (CASCADE) | Template being rated |
| `user_id` | String(100) | NOT NULL | User ID submitting rating |
| `rating` | Integer | NOT NULL | Numeric rating (1-5) |
| `comment` | Text | NULLABLE | Optional user review comment |
| `created_at` | DateTime(tz=True) | NOT NULL, DEFAULT=now() | Rating submission timestamp |
| `updated_at` | DateTime(tz=True) | NOT NULL, DEFAULT=now(), ONUPDATE=now() | Rating update timestamp |

**Relationships**:

- `template: Mapped[Template]`
  - Many-to-one relationship to Template
  - Provides access to rated template

**Constraints**:

- Unique constraint on (template_id, user_id) - one rating per user per template
- Cascade delete when parent template is deleted

**Methods**:

- `__repr__() -> str`: Returns rating info with template_id and rating value

---

##### `TemplateAnalytics` (ORM Model)

**Table**: `template_analytics`

**Purpose**: Tracks user interactions and usage metrics for templates

**Columns**:

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| `id` | Integer | PRIMARY KEY, AUTO INCREMENT | Unique event identifier |
| `template_id` | Integer | FOREIGN KEY → templates.id (CASCADE) | Template involved in event |
| `event_type` | String(50) | NOT NULL, INDEX | Event type (view, download, clone) |
| `user_id` | String(100) | NULLABLE, INDEX | User ID if authenticated |
| `ip_address` | String(45) | NULLABLE | IPv4/IPv6 address of user |
| `user_agent` | String(500) | NULLABLE | Browser user agent string |
| `metadata` | Text | NULLABLE | JSON string for flexible additional data |
| `created_at` | DateTime(tz=True) | NOT NULL, DEFAULT=now(), INDEX | Event timestamp |

**Indexes**:

- Composite index on (template_id, event_type, created_at) for analytics queries
- Separate indexes on event_type and created_at for filtering

**Methods**:

- `__repr__() -> str`: Returns analytics event info with template_id and event_type

---

### Configuration Layer

#### `config/settings.py` - Application Settings

**Location**: `/app/config/settings.py`

**Purpose**: Centralized configuration management using Pydantic BaseSettings

**Class**: `MarketplaceSettings(BaseSettings)`

**Configuration** (from `.env` or environment variables):

| Setting | Type | Default | Purpose | Env Alias |
|---------|------|---------|---------|-----------|
| `service_name` | str | "policy-marketplace" | Service identifier | SERVICE_NAME |
| `service_version` | str | "1.0.0" | Service version | SERVICE_VERSION |
| `port` | int | 8003 | HTTP server port | PORT |
| `host` | str | "0.0.0.0" | HTTP server bind address | HOST |
| `debug` | bool | False | Debug mode (enables logging, sqlalchemy echo) | DEBUG |
| `database_url` | str | "postgresql+asyncpg://postgres:postgres@localhost:5432/acgs2_marketplace" | PostgreSQL async connection string | MARKETPLACE_DATABASE_URL |
| `redis_url` | str | "redis://localhost:6379/0" | Redis connection string | REDIS_URL |
| `cors_origins` | List[str] | ["*"] | CORS allowed origins | MARKETPLACE_CORS_ORIGINS |

**Instance**: `settings = MarketplaceSettings()`
- Global singleton configuration object
- Used throughout application

---

### Schema Layer (Pydantic Models)

**Location**: `/app/schemas/template.py`

**Purpose**: Request/response validation and serialization using Pydantic v2

#### Enumerations

All enumerations follow the same pattern as database models:

- `TemplateStatus(str, Enum)`: DRAFT, PENDING_REVIEW, PUBLISHED, REJECTED, ARCHIVED
- `TemplateFormat(str, Enum)`: JSON, YAML, REGO
- `TemplateCategory(str, Enum)`: 9 policy categories
- `AnalyticsEventType(str, Enum)`: VIEW, DOWNLOAD, CLONE
- `ReviewAction(str, Enum)`: APPROVE, REJECT

#### Template Schemas

##### `TemplateBase(BaseModel)`

**Purpose**: Base schema with common template fields

**Fields**:

- `name: str` (min=1, max=255) - Template name
- `description: str` (min=1, max=5000) - Detailed description
- `category: TemplateCategory` - Policy category
- `format: TemplateFormat` (default=JSON) - File format

---

##### `TemplateCreate(TemplateBase)`

**Purpose**: Request schema for creating new templates

**Additional Fields**:

- `content: str` (min=1) - Template content (JSON/YAML/Rego)
- `is_public: bool` (default=True) - Public/private visibility
- `organization_id: Optional[str]` (max=100) - Organization for private templates

**Validators**:

- `validate_content_not_empty(v: str) -> str`
  - Ensures content is not just whitespace

---

##### `TemplateUpdate(BaseModel)`

**Purpose**: Request schema for partial template updates

**Fields** (all optional):

- `name: Optional[str]` - Template name
- `description: Optional[str]` - Template description
- `category: Optional[TemplateCategory]` - Policy category
- `content: Optional[str]` - Template content
- `is_public: Optional[bool]` - Visibility flag
- `status: Optional[TemplateStatus]` - Workflow status

---

##### `TemplateResponse(TemplateBase)`

**Purpose**: Response schema with full template details

**Fields**:

- `id: int` - Template ID
- `content: str` - Full template content
- `status: TemplateStatus` - Current workflow status
- `is_verified: bool` - Verification status
- `is_public: bool` - Public/private flag
- `organization_id: Optional[str]` - Organization ID
- `author_id: Optional[str]` - Creator user ID
- `author_name: Optional[str]` - Creator display name
- `current_version: str` - Semantic version
- `downloads: int` - Total download count
- `rating: Optional[float]` - Average rating (1-5)
- `rating_count: int` - Number of ratings
- `created_at: datetime` - Creation timestamp
- `updated_at: datetime` - Last update timestamp

**Serializers**:

- `serialize_datetime(value: datetime) -> str`
  - Converts datetime to ISO 8601 format

---

##### `TemplateListItem(BaseModel)`

**Purpose**: Lightweight schema for list responses (excludes content)

**Fields**: Same as TemplateResponse except:
- Excludes `content` field
- Includes all other fields for list display

---

#### Version Schemas

##### `VersionCreate(VersionBase)`

**Fields**:

- `content: str` (min=1) - Version content
- `changelog: Optional[str]` (max=5000) - Release notes

**Validators**:

- `validate_content_not_empty()` - Ensures non-empty content

---

##### `VersionResponse(VersionBase)`

**Fields**:

- `id: int` - Version ID
- `template_id: int` - Parent template ID
- `version: str` - Semantic version
- `content: str` - Version content
- `content_hash: str` - SHA-256 hash of content
- `created_by: Optional[str]` - Creator user ID
- `created_at: datetime` - Creation timestamp

---

##### `VersionListItem(BaseModel)`

**Purpose**: Lightweight version for list responses (excludes content)

**Fields**:

- `id: int` - Version ID
- `version: str` - Semantic version
- `changelog: Optional[str]` - Release notes
- `created_by: Optional[str]` - Creator user ID
- `created_at: datetime` - Creation timestamp

---

#### Rating Schemas

##### `RatingCreate(BaseModel)`

**Fields**:

- `rating: int` (min=1, max=5) - Numeric rating
- `comment: Optional[str]` (max=2000) - Review comment

---

##### `RatingResponse(BaseModel)`

**Fields**:

- `id: int` - Rating ID
- `template_id: int` - Template ID
- `user_id: str` - Rater user ID
- `rating: int` - Numeric rating (1-5)
- `comment: Optional[str]` - Review comment
- `created_at: datetime` - Submission timestamp
- `updated_at: datetime` - Update timestamp

---

#### Analytics Schemas

##### `AnalyticsResponse(BaseModel)`

**Fields**:

- `id: int` - Event ID
- `template_id: int` - Template ID
- `event_type: str` - Event type (view, download, clone)
- `user_id: Optional[str]` - User ID if authenticated
- `created_at: datetime` - Event timestamp

---

##### `TemplateAnalyticsSummary(BaseModel)`

**Fields**:

- `template_id: int` - Template ID
- `total_views: int` - View count
- `total_downloads: int` - Download count
- `total_clones: int` - Clone count
- `average_rating: Optional[float]` - Average rating
- `rating_count: int` - Number of ratings

---

##### `AnalyticsTrend(BaseModel)`

**Fields**:

- `date: str` - Date in YYYY-MM-DD format
- `views: int` (default=0) - View count for date
- `downloads: int` (default=0) - Download count for date

---

##### `AnalyticsDashboard(BaseModel)`

**Fields**:

- `start_date: str` - Period start date
- `end_date: str` - Period end date
- `total_templates: int` - Active template count
- `total_downloads: int` - Total downloads in period
- `total_views: int` - Total views in period
- `top_templates: List[TemplateListItem]` - Top 5 templates by downloads
- `trends: List[AnalyticsTrend]` - Daily trend data

---

#### Review Workflow Schemas

##### `ReviewRequest(BaseModel)`

**Fields**:

- `action: ReviewAction` - Action (approve, reject)
- `feedback: Optional[str]` (max=2000) - Reviewer feedback

---

##### `ReviewResponse(BaseModel)`

**Fields**:

- `template_id: int` - Template ID
- `action: ReviewAction` - Action taken
- `new_status: TemplateStatus` - New template status
- `reviewed_by: str` - Reviewer user ID
- `reviewed_at: datetime` - Review timestamp
- `feedback: Optional[str]` - Reviewer feedback

---

#### Pagination Schemas

##### `PaginationMeta(BaseModel)`

**Fields**:

- `page: int` (min=1) - Current page number
- `limit: int` (min=1, max=100) - Items per page
- `total_items: int` (min=0) - Total item count
- `total_pages: int` (min=0) - Total page count
- `has_next: bool` - Whether next page exists
- `has_prev: bool` - Whether previous page exists

---

##### `TemplateListResponse(BaseModel)`

**Fields**:

- `items: List[TemplateListItem]` - List of template items
- `meta: PaginationMeta` - Pagination metadata

---

##### `VersionListResponse(BaseModel)`

**Fields**:

- `items: List[VersionListItem]` - List of version items
- `meta: PaginationMeta` - Pagination metadata

---

#### Search & Filter Schemas

##### `TemplateSearchParams(BaseModel)`

**Fields** (all optional):

- `query: Optional[str]` (max=255) - Search query string
- `category: Optional[TemplateCategory]` - Filter by category
- `format: Optional[TemplateFormat]` - Filter by format
- `is_verified: Optional[bool]` - Filter by verification
- `organization_id: Optional[str]` (max=100) - Filter by organization
- `sort_by: str` (default="created_at") - Sort field
- `sort_order: str` (default="desc") - Sort direction (asc/desc)

**Validators**:

- `validate_sort_by()` - Validates against allowed fields: created_at, downloads, rating, name, updated_at
- `validate_sort_order()` - Ensures asc or desc (case-insensitive)

---

#### Error Response Schemas

##### `ErrorDetail(BaseModel)`

**Fields**:

- `loc: List[str]` - Error location (field path)
- `msg: str` - Error message
- `type: str` - Error type

---

##### `ErrorResponse(BaseModel)`

**Fields**:

- `detail: str` - Main error message
- `errors: Optional[List[ErrorDetail]]` - Validation error details

---

### API Layer (Routes)

**Location**: `/app/api/v1/`

**Base URL**: `/api/v1`

Each route module includes mock data stores for development/testing and implements business logic.

---

#### `templates.py` - Template CRUD Operations

**Location**: `/app/api/v1/templates.py`

**Purpose**: Implement template creation, retrieval, update, and deletion with access control

**Constants**:

- `ALLOWED_EXTENSIONS = {".json", ".yaml", ".yml", ".rego"}` - Valid file types
- `MAX_FILE_SIZE = 10 * 1024 * 1024` - 10MB upload limit

**Helper Classes**:

##### `UserContext`

**Purpose**: Extract and manage user authentication context from headers

**Constructor**:

```python
UserContext(
    user_id: Optional[str] = None,
    organization_id: Optional[str] = None,
    is_admin: bool = False
)
```

**Properties**:

- `is_authenticated: bool` - Returns True if user_id is set

---

**Helper Functions**:

- `get_user_context(x_user_id, x_organization_id, x_user_role) -> UserContext`
  - Extracts user context from request headers
  - Headers: X-User-Id, X-Organization-Id, X-User-Role

- `can_access_template(template, user_ctx) -> bool`
  - Implements access control rules:
    - Public templates: accessible to all
    - Private templates: only to same organization members
    - Admin users: access all templates

- `_to_list_item(template) -> TemplateListItem` - Converts dict to list schema

- `_to_response(template) -> TemplateResponse` - Converts dict to response schema

**Mock Data Store**:

- `_templates_store: Dict[int, Dict[str, Any]]` - In-memory storage
- `_next_id: int` - ID counter
- `_get_mock_templates() -> List[Dict]` - Seeds with 3 default templates

---

**Endpoints**:

##### `GET /` - List Templates

**Description**: List policy templates with pagination, filtering, and sorting

**Query Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | int | 1 | Page number (min=1) |
| `limit` | int | 20 | Items per page (1-100) |
| `category` | TemplateCategory | None | Filter by category |
| `format` | TemplateFormat | None | Filter by format |
| `is_verified` | bool | None | Filter by verification status |
| `query` | str | None | Search in name/description (max=255) |
| `sort_by` | str | "created_at" | Sort field (created_at, downloads, rating, name) |
| `sort_order` | str | "desc" | Sort order (asc, desc) |

**Headers**:

- `X-User-Id` (optional) - Authenticated user ID
- `X-Organization-Id` (optional) - User's organization
- `X-User-Role` (optional) - User role (determines admin status)

**Response**: `TemplateListResponse`
- `items: List[TemplateListItem]` - Paginated templates
- `meta: PaginationMeta` - Pagination info

**Access Control**: Respects public/private visibility

---

##### `POST /` - Create Template

**Description**: Create a new policy template

**Request Body**: `TemplateCreate`

**Response**: `TemplateResponse` (201 Created)

**Behavior**:

- Creates template in DRAFT status
- Sets is_verified to False
- Requires review workflow for publication
- Returns full template details

---

##### `POST /upload` - Upload Template File

**Description**: Upload a template file with validation

**Form Data**:

| Field | Type | Description |
|-------|------|-------------|
| `file` | UploadFile | Template file (.json, .yaml, .yml, .rego) |
| `name` | str | Template name (1-255 chars) |
| `description` | str | Template description (1-5000 chars) |
| `category` | str | Template category |
| `is_public` | bool | Public/private flag (default=True) |
| `organization_id` | str | Organization ID for private templates |

**Headers**:

- `X-User-Id` - User ID of uploader
- `X-Organization-Id` - User's organization

**Response**: `TemplateResponse` (201 Created)

**Validation**:

- File extension validation
- File size validation (max 10MB)
- UTF-8 encoding validation
- Category validation against enum

**Error Handling**:

- 400: Invalid file format or encoding
- 413: File too large

---

##### `GET /{template_id}` - Get Template

**Description**: Retrieve full template details by ID

**Path Parameters**:

- `template_id: int` - Template ID

**Headers**: User context headers (for access control)

**Response**: `TemplateResponse`

**Access Control**: Returns 404 for inaccessible private templates (avoids info disclosure)

---

##### `PUT /{template_id}` - Update Template

**Description**: Update template fields (partial update supported)

**Path Parameters**:

- `template_id: int` - Template ID

**Request Body**: `TemplateUpdate` (all fields optional)

**Response**: `TemplateResponse`

**Behavior**:

- Only provided fields are updated
- Updates `updated_at` timestamp
- Preserves unmodified fields

---

##### `DELETE /{template_id}` - Delete Template

**Description**: Soft delete a template

**Path Parameters**:

- `template_id: int` - Template ID

**Response**: 204 No Content

**Behavior**:

- Sets `is_deleted = True`
- Preserves analytics and download history
- Template excluded from list queries

---

##### `GET /{template_id}/download` - Download Template

**Description**: Download template content and track analytics

**Path Parameters**:

- `template_id: int` - Template ID

**Headers**: User context headers

**Response**:

```json
{
  "id": 1,
  "name": "Template Name",
  "content": "...",
  "format": "json",
  "version": "1.0.0",
  "downloads": 5
}
```

**Behavior**:

- Increments download counter
- Tracks analytics event
- Respects access control

---

#### `versions.py` - Template Versioning

**Location**: `/app/api/v1/versions.py`

**Purpose**: Implement semantic versioning for template content tracking

**Helper Functions**:

- `_compute_content_hash(content: str) -> str`
  - Computes SHA-256 hash of content
  - Used for integrity verification

- `_increment_version(version: str) -> str`
  - Increments patch version (e.g., 1.0.0 → 1.0.1)
  - Handles invalid format gracefully

- `_to_version_response()` - Converts dict to VersionResponse

- `_to_version_list_item()` - Converts dict to VersionListItem

**Mock Data Store**:

- `_versions_store: Dict[int, Dict[str, Any]]` - In-memory version storage
- `_next_version_id: int` - Version ID counter

---

**Endpoints**:

##### `POST /{template_id}/versions` - Create Version

**Description**: Create a new version for a template

**Path Parameters**:

- `template_id: int` - Template ID

**Request Body**: `VersionCreate`

**Response**: `VersionResponse` (201 Created)

**Behavior**:

- Automatically increments version number
- Computes content hash for integrity
- Updates template's current_version
- Creates audit trail entry

---

##### `GET /{template_id}/versions` - List Versions

**Description**: List all versions of a template

**Path Parameters**:

- `template_id: int` - Template ID

**Query Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | int | 1 | Page number |
| `limit` | int | 20 | Items per page (1-100) |

**Response**: `VersionListResponse`

**Behavior**:

- Returns versions in reverse chronological order (newest first)
- Automatically creates initial version from template content if needed
- Excludes content from list items

---

##### `GET /{template_id}/versions/{version_id}` - Get Version

**Description**: Retrieve specific version details

**Path Parameters**:

- `template_id: int` - Template ID
- `version_id: int` - Version ID

**Response**: `VersionResponse`

**Behavior**:

- Includes full content and hash
- Validates version belongs to template

---

##### `GET /{template_id}/versions/latest` - Get Latest Version

**Description**: Retrieve most recent version

**Path Parameters**:

- `template_id: int` - Template ID

**Response**: `VersionResponse`

**Behavior**:

- Returns latest version by creation date
- Falls back to synthetic version from template content if needed

---

#### `reviews.py` - Review Workflow

**Location**: `/app/api/v1/reviews.py`

**Purpose**: Implement community review workflow for template publication

**Mock Data Store**:

- `_reviews_store: Dict[int, Dict[str, Any]]` - Review records
- `_next_review_id: int` - Review ID counter

---

**Endpoints**:

##### `GET /pending` - List Pending Reviews

**Description**: List templates awaiting review

**Query Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | int | 1 | Page number |
| `limit` | int | 20 | Items per page |
| `category` | TemplateCategory | None | Filter by category |

**Response**: `TemplateListResponse`

**Behavior**:

- Returns templates in PENDING_REVIEW status
- Sorted by created_at ascending (FIFO processing)
- Admin-only access (production)

---

##### `POST /submit/{template_id}` - Submit for Review

**Description**: Submit template for community review

**Path Parameters**:

- `template_id: int` - Template ID

**Response**: `ReviewResponse` (200 OK)

**Validation**:

- Template must exist
- Must be in DRAFT status
- Returns 400 if already submitted

**Behavior**:

- Changes status: DRAFT → PENDING_REVIEW
- Creates audit trail entry
- Notifies reviewers

---

##### `POST /{template_id}/approve` - Approve Template

**Description**: Approve and publish a template

**Path Parameters**:

- `template_id: int` - Template ID

**Request Body**: `Optional[ReviewRequest]` (for feedback)

**Response**: `ReviewResponse` (200 OK)

**Validation**:

- Template must exist
- Must be in PENDING_REVIEW status

**Behavior**:

- Changes status: PENDING_REVIEW → PUBLISHED
- Sets is_verified = True
- Creates review record
- Admin-only action (production)

---

##### `POST /{template_id}/reject` - Reject Template

**Description**: Reject a template with feedback

**Path Parameters**:

- `template_id: int` - Template ID

**Request Body**: `Optional[ReviewRequest]` (for feedback)

**Response**: `ReviewResponse` (200 OK)

**Validation**:

- Template must exist
- Must be in PENDING_REVIEW status

**Behavior**:

- Changes status: PENDING_REVIEW → REJECTED
- Preserves is_verified = False
- Includes feedback message
- Admin-only action (production)

---

##### `GET /{template_id}/history` - Get Review History

**Description**: Retrieve complete review history for a template

**Path Parameters**:

- `template_id: int` - Template ID

**Response**: `List[ReviewResponse]`

**Behavior**:

- Returns all review actions in chronological order
- Includes submit, approve, and reject actions
- Provides complete audit trail

---

##### `POST /{template_id}/resubmit` - Resubmit for Review

**Description**: Resubmit a rejected template

**Path Parameters**:

- `template_id: int` - Template ID

**Response**: `ReviewResponse` (200 OK)

**Validation**:

- Template must exist
- Must be in REJECTED status

**Behavior**:

- Changes status: REJECTED → PENDING_REVIEW
- Allows author to address feedback and retry
- Creates new review record

---

#### `analytics.py` - Usage Analytics & Ratings

**Location**: `/app/api/v1/analytics.py`

**Purpose**: Track template usage metrics and community ratings

**Mock Data Stores**:

- `_analytics_store: Dict[int, Dict[str, Any]]` - Event records
- `_ratings_store: Dict[int, Dict[str, Any]]` - Rating records
- `_next_analytics_id: int` - Event ID counter
- `_next_rating_id: int` - Rating ID counter

---

**Analytics Endpoints**:

##### `GET /templates` - Analytics Dashboard

**Description**: Get aggregated marketplace analytics

**Query Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `start_date` | str | 30 days ago | Start date (YYYY-MM-DD) |
| `end_date` | str | Today | End date (YYYY-MM-DD) |

**Response**: `AnalyticsDashboard`

**Returns**:

- Total templates count
- Total downloads in period
- Total views in period
- Top 5 templates by downloads
- Daily trend data

---

##### `GET /templates/{template_id}` - Template Analytics

**Description**: Get analytics for specific template

**Path Parameters**:

- `template_id: int` - Template ID

**Response**: `TemplateAnalyticsSummary`

**Returns**:

- Total views
- Total downloads
- Total clones
- Average rating
- Rating count

---

##### `POST /templates/{template_id}/track` - Track Event

**Description**: Record an analytics event

**Path Parameters**:

- `template_id: int` - Template ID

**Query Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `event_type` | AnalyticsEventType | (required) | Event type (view, download, clone) |
| `user_id` | str | None | User ID if authenticated |

**Response**: `AnalyticsResponse` (201 Created)

**Behavior**:

- Creates analytics event record
- Increments template download counter if download event
- Tracks user context if provided

---

##### `GET /templates/{template_id}/events` - Get Events

**Description**: List analytics events for a template

**Path Parameters**:

- `template_id: int` - Template ID

**Query Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `event_type` | AnalyticsEventType | None | Filter by event type |
| `limit` | int | 50 | Max events to return (1-100) |

**Response**: `List[AnalyticsResponse]`

**Behavior**:

- Returns events in reverse chronological order (newest first)
- Optionally filters by event type

---

**Rating Endpoints**:

##### `POST /templates/{template_id}/rate` - Submit Rating

**Description**: Submit or update template rating

**Path Parameters**:

- `template_id: int` - Template ID

**Query Parameters**:

- `user_id: str` (default="anonymous") - User ID

**Request Body**: `RatingCreate`

**Response**: `RatingResponse` (201 Created)

**Behavior**:

- Creates new rating or updates existing (one per user per template)
- Updates template's average rating and rating_count
- Recalculates aggregates automatically

---

##### `GET /templates/{template_id}/ratings` - Get Ratings

**Description**: List ratings for a template

**Path Parameters**:

- `template_id: int` - Template ID

**Query Parameters**:

- `limit: int` (default=50) - Max ratings to return (1-100)

**Response**: `List[RatingResponse]`

**Behavior**:

- Returns ratings in reverse chronological order (newest first)
- Includes user comments and ratings

---

##### `GET /trends` - Analytics Trends

**Description**: Get daily analytics trends

**Query Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `days` | int | 30 | Number of days (1-90) |

**Response**: `List[AnalyticsTrend]`

**Behavior**:

- Returns daily view and download counts
- Useful for charting and trend analysis
- Covers specified number of days

---

### Router Integration

**Location**: `/app/api/v1/__init__.py`

**Purpose**: Combine all route modules into unified v1 API

**Router Assembly**:

```python
router = APIRouter()
router.include_router(templates_router, prefix="/templates", tags=["templates"])
router.include_router(versions_router, prefix="/templates", tags=["versions"])
router.include_router(reviews_router, prefix="/reviews", tags=["reviews"])
router.include_router(analytics_router, prefix="/analytics", tags=["analytics"])
```

**Route Structure**:

```
/api/v1/
├── /templates              (GET, POST, /{id}, DELETE, /{id}/download)
├── /templates/{id}/upload  (POST)
├── /templates/{id}/versions (GET, POST, /{version_id}, /latest)
├── /reviews/pending        (GET)
├── /reviews/submit/{id}    (POST)
├── /reviews/{id}/approve   (POST)
├── /reviews/{id}/reject    (POST)
├── /reviews/{id}/history   (GET)
├── /reviews/{id}/resubmit  (POST)
├── /analytics/templates    (GET)
├── /analytics/templates/{id} (GET)
├── /analytics/templates/{id}/track (POST)
├── /analytics/templates/{id}/events (GET)
├── /analytics/templates/{id}/rate (POST)
├── /analytics/templates/{id}/ratings (GET)
└── /analytics/trends       (GET)
```

---

## Dependencies

### Internal Dependencies

**From ACGS-2 Core**:

- `shared.security.cors_config` - CORS configuration (if available)
- `shared.security.rate_limiter` - Rate limiting (if available)
- `shared.config` - Global settings (if available)

**Within Service**:

- Models layer depends on database.py
- API routes depend on models and schemas
- Main app depends on all layers

### External Dependencies

**Core Framework**:

- FastAPI 0.115.6+
- Pydantic 2.0+ (with pydantic-settings)
- SQLAlchemy 2.0+ (asyncpg driver)

**Database**:

- PostgreSQL 14+ with Row-Level Security
- asyncpg for async SQL operations

**Utilities**:

- Python 3.11+ standard library (datetime, hashlib, enum, typing)
- asyncio for async operations

**Optional**:

- Redis (for caching, if integrated)
- Rate limiting libraries (from shared module)

---

## Key Data Structures

### Template Lifecycle State Machine

```
DRAFT ──submit──> PENDING_REVIEW ──approve──> PUBLISHED
                          │                        │
                          │                        │
                       reject           (end state for published)
                          │
                          ↓
                      REJECTED ──resubmit──> PENDING_REVIEW
```

### Version Control

**Semantic Versioning**: `major.minor.patch` (e.g., 1.0.0)

- Initial: 1.0.0
- Patch increments: 1.0.1, 1.0.2, ...
- Manual major/minor updates via content updates

**Content Hash**: SHA-256 digest for integrity verification

### Access Control Model

**Public Templates** (is_public=True):
- Accessible to all authenticated and anonymous users
- Downloadable by anyone
- Visible in public listings

**Organization-Private Templates** (is_public=False, organization_id set):
- Only accessible to users in same organization
- Requires X-Organization-Id header matching
- Admin users can access regardless

**User-Private Templates** (is_public=False, no organization_id):
- Only accessible to creator
- Not visible in public listings

### Rating Aggregation

- One rating per user per template
- Updates replace previous rating
- Average calculated from all ratings
- Rating count maintained for statistics

---

## API Response Patterns

### Success Responses

**Single Resource** (e.g., template creation):
```json
{
  "id": 1,
  "name": "Policy Name",
  ...
}
```

**Paginated List**:
```json
{
  "items": [...],
  "meta": {
    "page": 1,
    "limit": 20,
    "total_items": 100,
    "total_pages": 5,
    "has_next": true,
    "has_prev": false
  }
}
```

**Analytics**:
```json
{
  "start_date": "2024-01-01",
  "total_templates": 50,
  "trends": [...]
}
```

### Error Responses

**Validation Error** (400):
```json
{
  "detail": "Validation error",
  "errors": [
    {
      "loc": ["body", "name"],
      "msg": "string too short",
      "type": "value_error.str"
    }
  ]
}
```

**Not Found** (404):
```json
{
  "detail": "Template not found"
}
```

**Server Error** (500):
```json
{
  "detail": "Internal server error",
  "type": "ExceptionClassName"
}
```

---

## Integration Points

### With Policy Registry Service

The Policy Marketplace integrates with `policy_registry` service for:

- Policy template registration (future)
- Compliance verification (future)
- Cross-service policy validation (future)

### With Constitutional Framework

All operations validate against constitutional hash `cdd01ef066bc6cf2`:

- Template creation respects constitutional boundaries
- Review workflow enforces governance principles
- Analytics track constitutional compliance metrics

### With Authentication/Authorization

Headers-based authentication (production):

- `X-User-Id`: User identification
- `X-Organization-Id`: Organization membership
- `X-User-Role`: Role-based access (admin, user)
- `X-Internal-API-Key`: Service-to-service authentication

---

## Performance Characteristics

### Database Indexes

**Query Optimization**:

- Template listings (is_public, category, created_at indexes)
- User filters (organization_id index)
- Verification status (is_verified index)
- Version lookups (template_id, version unique constraint)
- Analytics queries (composite index on template_id, event_type, created_at)

### In-Memory Caching (Current)

Mock data stores use in-memory dictionaries:

- `_templates_store`: Single dictionary for all templates
- `_versions_store`: Single dictionary for all versions
- `_reviews_store`: Single dictionary for all reviews
- `_analytics_store`: Single dictionary for analytics events
- `_ratings_store`: Single dictionary for ratings

**Note**: Production implementation will use PostgreSQL directly

### Pagination

Default limits:

- Templates list: 20 per page (max 100)
- Versions list: 20 per page (max 100)
- Ratings list: 50 per page (max 100)
- Events list: 50 per page (max 100)
- Trends: up to 90 days

---

## Security Considerations

### Access Control

1. **Template Visibility**
   - Public templates visible to all
   - Private templates access-checked per-request
   - 404 returns for unauthorized access (information hiding)

2. **Review Workflow**
   - Submit: template owner only
   - Approve/Reject: admin only (production)
   - History: audit trail for all

3. **Rating/Analytics**
   - Write: any authenticated user
   - Read: public (analytics) or authenticated (individual)

### Input Validation

- Content length limits (1-5000 chars for descriptions)
- File size limits (10MB max upload)
- Category/format enum validation
- UTF-8 encoding verification
- Semantic version format validation

### Error Handling

- No information disclosure on private template access
- Detailed validation errors for client debugging
- Internal error logging without exposing details
- Graceful fallbacks for missing dependencies

---

## Future Enhancements

### Planned Features

1. **Database Integration**
   - Replace mock stores with PostgreSQL queries
   - Add connection pooling and optimization

2. **Advanced Versioning**
   - Diff tracking between versions
   - Version rollback capability
   - Change set management

3. **Enhanced Analytics**
   - Time-series forecasting
   - User journey tracking
   - Compliance pattern analysis

4. **Community Features**
   - Template forking/cloning
   - Collaborative editing
   - Discussion/comments

5. **Integration**
   - Policy registry synchronization
   - External policy source aggregation
   - Multi-region deployment

6. **Performance**
   - Redis caching layer
   - Full-text search with Elasticsearch
   - GraphQL API

---

## Mermaid Diagrams

### Class Diagram - Core Models

```mermaid
---
title: Policy Marketplace - Core Models
---
classDiagram
    namespace Models {
        class Template {
            int id
            str name
            str description
            str content
            str category
            str format
            str status
            bool is_verified
            bool is_public
            str organization_id
            str author_id
            str current_version
            int downloads
            float rating
            int rating_count
            bool is_deleted
            datetime created_at
            datetime updated_at
        }

        class TemplateVersion {
            int id
            int template_id
            str version
            str content
            str content_hash
            str changelog
            str created_by
            datetime created_at
        }

        class TemplateRating {
            int id
            int template_id
            str user_id
            int rating
            str comment
            datetime created_at
            datetime updated_at
        }

        class TemplateAnalytics {
            int id
            int template_id
            str event_type
            str user_id
            str ip_address
            str user_agent
            str metadata
            datetime created_at
        }
    }

    Template "1" -- "*" TemplateVersion : versions
    Template "1" -- "*" TemplateRating : ratings
    Template "1" -- "*" TemplateAnalytics : events
```

### API Request Flow - Template Creation

```mermaid
---
title: Template Creation Flow
---
flowchart LR
    Client["Client"]
    Auth["Auth Middleware<br/>(X-Internal-API-Key)"]
    RateLimit["Rate Limiter<br/>(Optional)"]
    Handler["POST /api/v1/templates<br/>create_template()"]
    Schema["TemplateCreate<br/>(Validation)"]
    Store["_templates_store<br/>(Mock DB)"]
    Response["TemplateResponse<br/>(201 Created)"]

    Client -->|Request| Auth
    Auth -->|Valid| RateLimit
    RateLimit -->|Allowed| Handler
    Handler -->|Parse Body| Schema
    Schema -->|Validate| Handler
    Handler -->|Store| Store
    Store -->|Success| Response
    Response -->|JSON| Client
```

### API Request Flow - Review Workflow

```mermaid
---
title: Template Review Workflow
---
flowchart TB
    Draft["DRAFT Status<br/>(New Template)"]
    Submit["POST /reviews/submit/{id}<br/>(Author)"]
    Pending["PENDING_REVIEW Status<br/>(Awaiting Review)"]
    Approve["POST /reviews/{id}/approve<br/>(Admin)"]
    Reject["POST /reviews/{id}/reject<br/>(Admin)"]
    Published["PUBLISHED Status<br/>(Public Access)"]
    Rejected["REJECTED Status<br/>(Author Notified)"]
    Resubmit["POST /reviews/{id}/resubmit<br/>(Author)"]

    Draft -->|Submit| Submit
    Submit --> Pending
    Pending -->|Approve| Approve
    Approve --> Published
    Pending -->|Reject| Reject
    Reject --> Rejected
    Rejected -->|Resubmit| Resubmit
    Resubmit --> Pending
```

### Data Structure - Pagination Response

```mermaid
---
title: Paginated List Response Structure
---
classDiagram
    namespace Response {
        class TemplateListResponse {
            List~TemplateListItem~ items
            PaginationMeta meta
        }

        class TemplateListItem {
            int id
            str name
            str description
            TemplateCategory category
            TemplateFormat format
            TemplateStatus status
            bool is_verified
            bool is_public
            str author_name
            str current_version
            int downloads
            float rating
            int rating_count
            datetime created_at
            datetime updated_at
        }

        class PaginationMeta {
            int page
            int limit
            int total_items
            int total_pages
            bool has_next
            bool has_prev
        }
    }

    TemplateListResponse "1" -- "*" TemplateListItem : items
    TemplateListResponse "1" -- "1" PaginationMeta : meta
```

---

## Notes

### Development vs. Production

**Current Implementation** (Development/Testing):

- Mock in-memory data stores
- No actual database persistence
- Used for API prototyping and testing
- All data lost on restart

**Production Path**:

1. Replace `_*_store` dictionaries with database queries
2. Implement proper async repository pattern
3. Add connection pooling and query optimization
4. Integrate Redis caching layer
5. Add real authentication/authorization
6. Enable comprehensive logging and monitoring

### Code Structure Patterns

**Each API route module**:

1. Constants and configuration
2. Mock data stores
3. Helper functions for data transformation
4. API endpoint definitions
5. Error handling and validation

**Helper Functions** follow patterns:

- `_get_*_store()`: Access to data
- `_to_*_schema()`: Dict to Pydantic conversion
- `_*_validator()`: Input validation
- `_*_handler()`: Business logic

### Testing Considerations

**Mock Data Seeds** in `_get_mock_templates()`:

- 3 pre-populated templates for testing
- Represents different categories
- Used for list/filter/sort verification

**Access Control** in `can_access_template()`:

- Test public vs. private visibility
- Test organization-based access
- Test admin override capability

**Error Scenarios**:

- Invalid IDs (404 responses)
- Deleted templates (soft delete)
- Invalid state transitions (400 responses)
- File upload validation (extension, size, encoding)

---

**Constitutional Hash**: `cdd01ef066bc6cf2` - Immutable governance validation across all operations
