"""
ACGS-2 Admin API for SSO Provider Configuration
Constitutional Hash: cdd01ef066bc6cf2

Provides administrative endpoints for managing SSO providers and role mappings.
These endpoints require admin authentication and authorization.

Endpoints:
    SSO Providers:
    - POST /providers - Create a new SSO provider
    - GET /providers - List all SSO providers
    - GET /providers/{provider_id} - Get a specific SSO provider
    - PUT /providers/{provider_id} - Update an SSO provider
    - DELETE /providers/{provider_id} - Delete an SSO provider

    Role Mappings:
    - POST /role-mappings - Create a new role mapping
    - GET /role-mappings - List all role mappings
    - GET /role-mappings/{mapping_id} - Get a specific role mapping
    - PUT /role-mappings/{mapping_id} - Update a role mapping
    - DELETE /role-mappings/{mapping_id} - Delete a role mapping
"""

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, field_validator

from shared.config import settings

# Configure logging
logger = logging.getLogger(__name__)

# Constitutional hash constant
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

# Create router with admin prefix
router = APIRouter(tags=["Admin SSO"])

# Security bearer token handler
security = HTTPBearer(auto_error=False)

# In-memory storage for development (replace with database in production)
# This mimics database storage until proper database sessions are wired up
_sso_providers: dict[str, dict[str, Any]] = {}
_role_mappings: dict[str, dict[str, Any]] = {}


# ========================================
# Request/Response Models
# ========================================


class SSOProviderCreateRequest(BaseModel):
    """Request model for creating an SSO provider with validation."""

    name: str = Field(..., min_length=1, max_length=255, description="Human-readable provider name")
    type: str = Field(..., description="Provider type: 'oidc' or 'saml'")
    enabled: bool = Field(default=True, description="Whether this provider is active")

    # OIDC-specific fields
    oidc_client_id: Optional[str] = Field(None, max_length=255, description="OAuth 2.0 client ID")
    oidc_client_secret: Optional[str] = Field(
        None, max_length=512, description="OAuth 2.0 client secret"
    )
    oidc_metadata_url: Optional[str] = Field(
        None, max_length=1024, description="OIDC discovery URL"
    )
    oidc_scopes: Optional[str] = Field(
        "openid profile email", max_length=512, description="Space-separated OAuth scopes"
    )

    # SAML-specific fields
    saml_entity_id: Optional[str] = Field(None, max_length=1024, description="IdP entity ID")
    saml_metadata_url: Optional[str] = Field(None, max_length=1024, description="IdP metadata URL")
    saml_metadata_xml: Optional[str] = Field(None, description="Cached IdP metadata XML")
    saml_sp_cert: Optional[str] = Field(None, description="SP certificate in PEM format")
    saml_sp_key: Optional[str] = Field(None, description="SP private key in PEM format")
    saml_sign_requests: bool = Field(True, description="Whether to sign SAML AuthnRequests")
    saml_sign_assertions: bool = Field(True, description="Whether IdP should sign assertions")

    # General fields
    allowed_domains: Optional[list[str]] = Field(None, description="List of allowed email domains")
    default_roles: Optional[list[str]] = Field(None, description="Default roles for new users")
    config: Optional[dict[str, Any]] = Field(
        None, description="Additional provider-specific configuration"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate provider name format."""
        if not re.match(r"^[a-zA-Z0-9_\- ]+$", v):
            raise ValueError(
                "Name must contain only alphanumeric characters, spaces, hyphens, and underscores"
            )
        return v.strip()

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        """Validate provider type."""
        v_lower = v.lower()
        if v_lower not in ("oidc", "saml"):
            raise ValueError("Type must be 'oidc' or 'saml'")
        return v_lower


class SSOProviderUpdateRequest(BaseModel):
    """Request model for updating an SSO provider."""

    name: Optional[str] = Field(
        None, min_length=1, max_length=255, description="Human-readable provider name"
    )
    enabled: Optional[bool] = Field(None, description="Whether this provider is active")

    # OIDC-specific fields
    oidc_client_id: Optional[str] = Field(None, max_length=255, description="OAuth 2.0 client ID")
    oidc_client_secret: Optional[str] = Field(
        None, max_length=512, description="OAuth 2.0 client secret"
    )
    oidc_metadata_url: Optional[str] = Field(
        None, max_length=1024, description="OIDC discovery URL"
    )
    oidc_scopes: Optional[str] = Field(
        None, max_length=512, description="Space-separated OAuth scopes"
    )

    # SAML-specific fields
    saml_entity_id: Optional[str] = Field(None, max_length=1024, description="IdP entity ID")
    saml_metadata_url: Optional[str] = Field(None, max_length=1024, description="IdP metadata URL")
    saml_metadata_xml: Optional[str] = Field(None, description="Cached IdP metadata XML")
    saml_sp_cert: Optional[str] = Field(None, description="SP certificate in PEM format")
    saml_sp_key: Optional[str] = Field(None, description="SP private key in PEM format")
    saml_sign_requests: Optional[bool] = Field(
        None, description="Whether to sign SAML AuthnRequests"
    )
    saml_sign_assertions: Optional[bool] = Field(
        None, description="Whether IdP should sign assertions"
    )

    # General fields
    allowed_domains: Optional[list[str]] = Field(None, description="List of allowed email domains")
    default_roles: Optional[list[str]] = Field(None, description="Default roles for new users")
    config: Optional[dict[str, Any]] = Field(
        None, description="Additional provider-specific configuration"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate provider name format."""
        if v is None:
            return None
        if not re.match(r"^[a-zA-Z0-9_\- ]+$", v):
            raise ValueError(
                "Name must contain only alphanumeric characters, spaces, hyphens, and underscores"
            )
        return v.strip()


class SSOProviderResponse(BaseModel):
    """Response model for SSO provider data."""

    id: str = Field(..., description="Provider UUID")
    name: str = Field(..., description="Provider name")
    type: str = Field(..., description="Provider type (oidc or saml)")
    enabled: bool = Field(..., description="Whether provider is active")

    # OIDC fields (secrets masked)
    oidc_client_id: Optional[str] = Field(None, description="OAuth client ID")
    oidc_metadata_url: Optional[str] = Field(None, description="OIDC discovery URL")
    oidc_scopes: Optional[str] = Field(None, description="OAuth scopes")

    # SAML fields
    saml_entity_id: Optional[str] = Field(None, description="IdP entity ID")
    saml_metadata_url: Optional[str] = Field(None, description="IdP metadata URL")
    saml_sign_requests: Optional[bool] = Field(None, description="Sign requests")
    saml_sign_assertions: Optional[bool] = Field(None, description="Sign assertions")

    # General fields
    allowed_domains: Optional[list[str]] = Field(None, description="Allowed email domains")
    default_roles: Optional[list[str]] = Field(None, description="Default roles")

    # Timestamps
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")


class RoleMappingCreateRequest(BaseModel):
    """Request model for creating a role mapping."""

    provider_id: str = Field(..., min_length=1, max_length=36, description="SSO provider UUID")
    idp_group: str = Field(..., min_length=1, max_length=255, description="IdP group name")
    acgs_role: str = Field(..., min_length=1, max_length=100, description="ACGS-2 role identifier")
    priority: int = Field(default=0, ge=0, le=100, description="Mapping priority (0-100)")
    description: Optional[str] = Field(None, max_length=500, description="Optional description")

    @field_validator("idp_group", "acgs_role")
    @classmethod
    def validate_names(cls, v: str) -> str:
        """Validate group and role name formats."""
        if not re.match(r"^[a-zA-Z0-9_\-:. ]+$", v):
            raise ValueError(
                "Name must contain only alphanumeric characters, spaces, hyphens, "
                "underscores, colons, and periods"
            )
        return v.strip()


class RoleMappingUpdateRequest(BaseModel):
    """Request model for updating a role mapping."""

    idp_group: Optional[str] = Field(
        None, min_length=1, max_length=255, description="IdP group name"
    )
    acgs_role: Optional[str] = Field(
        None, min_length=1, max_length=100, description="ACGS-2 role identifier"
    )
    priority: Optional[int] = Field(None, ge=0, le=100, description="Mapping priority (0-100)")
    description: Optional[str] = Field(None, max_length=500, description="Optional description")

    @field_validator("idp_group", "acgs_role")
    @classmethod
    def validate_names(cls, v: Optional[str]) -> Optional[str]:
        """Validate group and role name formats."""
        if v is None:
            return None
        if not re.match(r"^[a-zA-Z0-9_\-:. ]+$", v):
            raise ValueError(
                "Name must contain only alphanumeric characters, spaces, hyphens, "
                "underscores, colons, and periods"
            )
        return v.strip()


class RoleMappingResponse(BaseModel):
    """Response model for role mapping data."""

    id: str = Field(..., description="Mapping UUID")
    provider_id: str = Field(..., description="SSO provider UUID")
    idp_group: str = Field(..., description="IdP group name")
    acgs_role: str = Field(..., description="ACGS-2 role identifier")
    priority: int = Field(..., description="Mapping priority")
    description: Optional[str] = Field(None, description="Optional description")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")


# ========================================
# Authentication & Authorization
# ========================================


async def get_current_admin(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),  # noqa: B008
) -> dict[str, Any]:
    """Validate admin authentication and authorization.

    This function checks for admin authentication via:
    1. Session-based auth (from SSO login)
    2. Bearer token auth (for API access)

    Args:
        request: The incoming request
        credentials: Optional bearer token credentials

    Returns:
        User dict with role information

    Raises:
        HTTPException: If not authenticated or not authorized as admin
    """
    # Check session-based auth first
    user = request.session.get("user")
    if user:
        roles = user.get("roles", [])
        if "admin" in roles or "sso-admin" in roles:
            logger.info(
                "Admin access granted via session",
                extra={
                    "user_id": user.get("id"),
                    "email": user.get("email"),
                    "constitutional_hash": CONSTITUTIONAL_HASH,
                },
            )
            return user
        else:
            logger.warning(
                "Session user lacks admin role",
                extra={
                    "user_id": user.get("id"),
                    "roles": roles,
                    "constitutional_hash": CONSTITUTIONAL_HASH,
                },
            )
            raise HTTPException(
                status_code=403,
                detail="Admin role required for this operation.",
            )

    # Check bearer token auth
    if credentials:
        # In production, validate JWT token here
        # For now, check for a dev admin token
        token = credentials.credentials
        if (
            token == settings.security.admin_api_key
            if hasattr(settings.security, "admin_api_key")
            else False
        ):
            logger.info(
                "Admin access granted via API key",
                extra={"constitutional_hash": CONSTITUTIONAL_HASH},
            )
            return {"id": "api-admin", "roles": ["admin"], "auth_type": "api_key"}

        # Attempt JWT validation if crypto service available
        try:
            from shared.crypto import CryptoService

            crypto_service = CryptoService()
            public_key = (
                settings.security.jwt_public_key
                if hasattr(settings.security, "jwt_public_key")
                else None
            )
            if public_key:
                payload = crypto_service.verify_agent_token(token, public_key)
                if "admin" in payload.get("roles", []):
                    return payload
        except ImportError:
            pass
        except Exception as e:
            logger.debug(f"JWT validation failed: {e}")

    # Check for development mode bypass
    if settings.env == "development" and settings.sso.enabled is False:
        # Allow admin access in development when SSO is disabled
        logger.warning(
            "Development admin bypass enabled - SSO disabled",
            extra={"constitutional_hash": CONSTITUTIONAL_HASH},
        )
        return {"id": "dev-admin", "roles": ["admin"], "auth_type": "dev_bypass"}

    # No valid authentication found
    logger.warning(
        "Admin access denied - no valid authentication",
        extra={
            "has_session": bool(user),
            "has_credentials": bool(credentials),
            "constitutional_hash": CONSTITUTIONAL_HASH,
        },
    )
    raise HTTPException(
        status_code=401,
        detail="Admin authentication required.",
    )


# ========================================
# SSO Provider CRUD Endpoints
# ========================================


@router.post("/providers", response_model=SSOProviderResponse, status_code=201)
async def create_sso_provider(
    request_data: SSOProviderCreateRequest,
    admin: dict[str, Any] = Depends(get_current_admin),
) -> SSOProviderResponse:
    """Create a new SSO provider configuration.

    This endpoint creates a new SAML or OIDC provider configuration
    that can be used for enterprise SSO authentication.

    Args:
        request_data: Provider configuration data
        admin: Authenticated admin user

    Returns:
        Created provider data

    Raises:
        HTTPException: If provider name already exists or validation fails
    """
    # Check for duplicate name
    for provider in _sso_providers.values():
        if provider["name"].lower() == request_data.name.lower():
            raise HTTPException(
                status_code=409,
                detail=f"SSO provider with name '{request_data.name}' already exists.",
            )

    # Validate OIDC config
    if request_data.type == "oidc":
        if not request_data.oidc_client_id:
            raise HTTPException(
                status_code=400,
                detail="OIDC provider requires oidc_client_id.",
            )
        if not request_data.oidc_client_secret:
            raise HTTPException(
                status_code=400,
                detail="OIDC provider requires oidc_client_secret.",
            )
        if not request_data.oidc_metadata_url:
            raise HTTPException(
                status_code=400,
                detail="OIDC provider requires oidc_metadata_url.",
            )

    # Validate SAML config
    if request_data.type == "saml":
        if not request_data.saml_entity_id and not request_data.saml_metadata_url:
            raise HTTPException(
                status_code=400,
                detail="SAML provider requires either saml_entity_id or saml_metadata_url.",
            )

    # Generate provider ID and timestamps
    provider_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    # Create provider record
    provider = {
        "id": provider_id,
        "name": request_data.name,
        "type": request_data.type,
        "enabled": request_data.enabled,
        # OIDC fields
        "oidc_client_id": request_data.oidc_client_id,
        "oidc_client_secret": request_data.oidc_client_secret,
        "oidc_metadata_url": request_data.oidc_metadata_url,
        "oidc_scopes": request_data.oidc_scopes,
        # SAML fields
        "saml_entity_id": request_data.saml_entity_id,
        "saml_metadata_url": request_data.saml_metadata_url,
        "saml_metadata_xml": request_data.saml_metadata_xml,
        "saml_sp_cert": request_data.saml_sp_cert,
        "saml_sp_key": request_data.saml_sp_key,
        "saml_sign_requests": request_data.saml_sign_requests,
        "saml_sign_assertions": request_data.saml_sign_assertions,
        # General fields
        "allowed_domains": request_data.allowed_domains or [],
        "default_roles": request_data.default_roles or [],
        "config": request_data.config or {},
        # Timestamps
        "created_at": now,
        "updated_at": now,
    }

    # Store provider
    _sso_providers[provider_id] = provider

    logger.info(
        "SSO provider created",
        extra={
            "provider_id": provider_id,
            "name": request_data.name,
            "type": request_data.type,
            "admin_id": admin.get("id"),
            "constitutional_hash": CONSTITUTIONAL_HASH,
        },
    )

    # Return response (without secrets)
    return SSOProviderResponse(
        id=provider["id"],
        name=provider["name"],
        type=provider["type"],
        enabled=provider["enabled"],
        oidc_client_id=provider["oidc_client_id"],
        oidc_metadata_url=provider["oidc_metadata_url"],
        oidc_scopes=provider["oidc_scopes"],
        saml_entity_id=provider["saml_entity_id"],
        saml_metadata_url=provider["saml_metadata_url"],
        saml_sign_requests=provider["saml_sign_requests"],
        saml_sign_assertions=provider["saml_sign_assertions"],
        allowed_domains=provider["allowed_domains"],
        default_roles=provider["default_roles"],
        created_at=provider["created_at"],
        updated_at=provider["updated_at"],
    )


@router.get("/providers", response_model=list[SSOProviderResponse])
async def list_sso_providers(
    enabled_only: bool = Query(False, description="Only return enabled providers"),
    provider_type: Optional[str] = Query(None, description="Filter by type (oidc/saml)"),
    admin: dict[str, Any] = Depends(get_current_admin),
) -> list[SSOProviderResponse]:
    """List all SSO provider configurations.

    Args:
        enabled_only: If True, only return enabled providers
        provider_type: Filter by provider type
        admin: Authenticated admin user

    Returns:
        List of SSO providers
    """
    providers = []

    for provider in _sso_providers.values():
        # Apply filters
        if enabled_only and not provider["enabled"]:
            continue
        if provider_type and provider["type"] != provider_type.lower():
            continue

        providers.append(
            SSOProviderResponse(
                id=provider["id"],
                name=provider["name"],
                type=provider["type"],
                enabled=provider["enabled"],
                oidc_client_id=provider.get("oidc_client_id"),
                oidc_metadata_url=provider.get("oidc_metadata_url"),
                oidc_scopes=provider.get("oidc_scopes"),
                saml_entity_id=provider.get("saml_entity_id"),
                saml_metadata_url=provider.get("saml_metadata_url"),
                saml_sign_requests=provider.get("saml_sign_requests"),
                saml_sign_assertions=provider.get("saml_sign_assertions"),
                allowed_domains=provider.get("allowed_domains", []),
                default_roles=provider.get("default_roles", []),
                created_at=provider["created_at"],
                updated_at=provider["updated_at"],
            )
        )

    logger.info(
        "SSO providers listed",
        extra={
            "count": len(providers),
            "enabled_only": enabled_only,
            "provider_type": provider_type,
            "admin_id": admin.get("id"),
            "constitutional_hash": CONSTITUTIONAL_HASH,
        },
    )

    return providers


@router.get("/providers/{provider_id}", response_model=SSOProviderResponse)
async def get_sso_provider(
    provider_id: str,
    admin: dict[str, Any] = Depends(get_current_admin),
) -> SSOProviderResponse:
    """Get a specific SSO provider configuration.

    Args:
        provider_id: Provider UUID
        admin: Authenticated admin user

    Returns:
        SSO provider data

    Raises:
        HTTPException: If provider not found
    """
    provider = _sso_providers.get(provider_id)
    if not provider:
        raise HTTPException(
            status_code=404,
            detail=f"SSO provider '{provider_id}' not found.",
        )

    return SSOProviderResponse(
        id=provider["id"],
        name=provider["name"],
        type=provider["type"],
        enabled=provider["enabled"],
        oidc_client_id=provider.get("oidc_client_id"),
        oidc_metadata_url=provider.get("oidc_metadata_url"),
        oidc_scopes=provider.get("oidc_scopes"),
        saml_entity_id=provider.get("saml_entity_id"),
        saml_metadata_url=provider.get("saml_metadata_url"),
        saml_sign_requests=provider.get("saml_sign_requests"),
        saml_sign_assertions=provider.get("saml_sign_assertions"),
        allowed_domains=provider.get("allowed_domains", []),
        default_roles=provider.get("default_roles", []),
        created_at=provider["created_at"],
        updated_at=provider["updated_at"],
    )


@router.put("/providers/{provider_id}", response_model=SSOProviderResponse)
async def update_sso_provider(
    provider_id: str,
    request_data: SSOProviderUpdateRequest,
    admin: dict[str, Any] = Depends(get_current_admin),
) -> SSOProviderResponse:
    """Update an SSO provider configuration.

    Args:
        provider_id: Provider UUID
        request_data: Updated provider configuration
        admin: Authenticated admin user

    Returns:
        Updated provider data

    Raises:
        HTTPException: If provider not found or name conflict
    """
    provider = _sso_providers.get(provider_id)
    if not provider:
        raise HTTPException(
            status_code=404,
            detail=f"SSO provider '{provider_id}' not found.",
        )

    # Check for name conflict
    if request_data.name:
        for pid, p in _sso_providers.items():
            if pid != provider_id and p["name"].lower() == request_data.name.lower():
                raise HTTPException(
                    status_code=409,
                    detail=f"SSO provider with name '{request_data.name}' already exists.",
                )

    # Update fields if provided
    update_data = request_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            provider[field] = value

    # Update timestamp
    provider["updated_at"] = datetime.now(timezone.utc).isoformat()

    logger.info(
        "SSO provider updated",
        extra={
            "provider_id": provider_id,
            "updated_fields": list(update_data.keys()),
            "admin_id": admin.get("id"),
            "constitutional_hash": CONSTITUTIONAL_HASH,
        },
    )

    return SSOProviderResponse(
        id=provider["id"],
        name=provider["name"],
        type=provider["type"],
        enabled=provider["enabled"],
        oidc_client_id=provider.get("oidc_client_id"),
        oidc_metadata_url=provider.get("oidc_metadata_url"),
        oidc_scopes=provider.get("oidc_scopes"),
        saml_entity_id=provider.get("saml_entity_id"),
        saml_metadata_url=provider.get("saml_metadata_url"),
        saml_sign_requests=provider.get("saml_sign_requests"),
        saml_sign_assertions=provider.get("saml_sign_assertions"),
        allowed_domains=provider.get("allowed_domains", []),
        default_roles=provider.get("default_roles", []),
        created_at=provider["created_at"],
        updated_at=provider["updated_at"],
    )


@router.delete("/providers/{provider_id}", status_code=204)
async def delete_sso_provider(
    provider_id: str,
    admin: dict[str, Any] = Depends(get_current_admin),
) -> None:
    """Delete an SSO provider configuration.

    This also deletes all associated role mappings.

    Args:
        provider_id: Provider UUID
        admin: Authenticated admin user

    Raises:
        HTTPException: If provider not found
    """
    if provider_id not in _sso_providers:
        raise HTTPException(
            status_code=404,
            detail=f"SSO provider '{provider_id}' not found.",
        )

    # Delete associated role mappings
    mappings_to_delete = [
        mapping_id
        for mapping_id, mapping in _role_mappings.items()
        if mapping["provider_id"] == provider_id
    ]
    for mapping_id in mappings_to_delete:
        del _role_mappings[mapping_id]

    # Delete provider
    provider_name = _sso_providers[provider_id]["name"]
    del _sso_providers[provider_id]

    logger.info(
        "SSO provider deleted",
        extra={
            "provider_id": provider_id,
            "provider_name": provider_name,
            "deleted_mappings": len(mappings_to_delete),
            "admin_id": admin.get("id"),
            "constitutional_hash": CONSTITUTIONAL_HASH,
        },
    )


# ========================================
# Role Mapping CRUD Endpoints
# ========================================


@router.post("/role-mappings", response_model=RoleMappingResponse, status_code=201)
async def create_role_mapping(
    request_data: RoleMappingCreateRequest,
    admin: dict[str, Any] = Depends(get_current_admin),
) -> RoleMappingResponse:
    """Create a new IdP group to role mapping.

    Maps an identity provider group to an ACGS-2 internal role.
    When users authenticate via SSO, their IdP group memberships
    are translated to roles using these mappings.

    Args:
        request_data: Role mapping configuration
        admin: Authenticated admin user

    Returns:
        Created role mapping data

    Raises:
        HTTPException: If provider not found or mapping already exists
    """
    # Verify provider exists
    if request_data.provider_id not in _sso_providers:
        raise HTTPException(
            status_code=404,
            detail=f"SSO provider '{request_data.provider_id}' not found.",
        )

    # Check for duplicate mapping (same provider + idp_group)
    for mapping in _role_mappings.values():
        if (
            mapping["provider_id"] == request_data.provider_id
            and mapping["idp_group"].lower() == request_data.idp_group.lower()
        ):
            raise HTTPException(
                status_code=409,
                detail=f"Mapping for group '{request_data.idp_group}' already exists for this provider.",
            )

    # Generate mapping ID and timestamps
    mapping_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    # Create mapping record
    mapping = {
        "id": mapping_id,
        "provider_id": request_data.provider_id,
        "idp_group": request_data.idp_group,
        "acgs_role": request_data.acgs_role,
        "priority": request_data.priority,
        "description": request_data.description,
        "created_at": now,
        "updated_at": now,
    }

    # Store mapping
    _role_mappings[mapping_id] = mapping

    logger.info(
        "Role mapping created",
        extra={
            "mapping_id": mapping_id,
            "provider_id": request_data.provider_id,
            "idp_group": request_data.idp_group,
            "acgs_role": request_data.acgs_role,
            "admin_id": admin.get("id"),
            "constitutional_hash": CONSTITUTIONAL_HASH,
        },
    )

    return RoleMappingResponse(
        id=mapping["id"],
        provider_id=mapping["provider_id"],
        idp_group=mapping["idp_group"],
        acgs_role=mapping["acgs_role"],
        priority=mapping["priority"],
        description=mapping["description"],
        created_at=mapping["created_at"],
        updated_at=mapping["updated_at"],
    )


@router.get("/role-mappings", response_model=list[RoleMappingResponse])
async def list_role_mappings(
    provider_id: Optional[str] = Query(None, description="Filter by SSO provider ID"),
    acgs_role: Optional[str] = Query(None, description="Filter by ACGS-2 role"),
    admin: dict[str, Any] = Depends(get_current_admin),
) -> list[RoleMappingResponse]:
    """List all role mappings.

    Args:
        provider_id: Filter by SSO provider UUID
        acgs_role: Filter by ACGS-2 role name
        admin: Authenticated admin user

    Returns:
        List of role mappings
    """
    mappings = []

    for mapping in _role_mappings.values():
        # Apply filters
        if provider_id and mapping["provider_id"] != provider_id:
            continue
        if acgs_role and mapping["acgs_role"].lower() != acgs_role.lower():
            continue

        mappings.append(
            RoleMappingResponse(
                id=mapping["id"],
                provider_id=mapping["provider_id"],
                idp_group=mapping["idp_group"],
                acgs_role=mapping["acgs_role"],
                priority=mapping["priority"],
                description=mapping["description"],
                created_at=mapping["created_at"],
                updated_at=mapping["updated_at"],
            )
        )

    # Sort by priority (descending)
    mappings.sort(key=lambda m: m.priority, reverse=True)

    logger.info(
        "Role mappings listed",
        extra={
            "count": len(mappings),
            "provider_id": provider_id,
            "acgs_role": acgs_role,
            "admin_id": admin.get("id"),
            "constitutional_hash": CONSTITUTIONAL_HASH,
        },
    )

    return mappings


@router.get("/role-mappings/{mapping_id}", response_model=RoleMappingResponse)
async def get_role_mapping(
    mapping_id: str,
    admin: dict[str, Any] = Depends(get_current_admin),
) -> RoleMappingResponse:
    """Get a specific role mapping.

    Args:
        mapping_id: Role mapping UUID
        admin: Authenticated admin user

    Returns:
        Role mapping data

    Raises:
        HTTPException: If mapping not found
    """
    mapping = _role_mappings.get(mapping_id)
    if not mapping:
        raise HTTPException(
            status_code=404,
            detail=f"Role mapping '{mapping_id}' not found.",
        )

    return RoleMappingResponse(
        id=mapping["id"],
        provider_id=mapping["provider_id"],
        idp_group=mapping["idp_group"],
        acgs_role=mapping["acgs_role"],
        priority=mapping["priority"],
        description=mapping["description"],
        created_at=mapping["created_at"],
        updated_at=mapping["updated_at"],
    )


@router.put("/role-mappings/{mapping_id}", response_model=RoleMappingResponse)
async def update_role_mapping(
    mapping_id: str,
    request_data: RoleMappingUpdateRequest,
    admin: dict[str, Any] = Depends(get_current_admin),
) -> RoleMappingResponse:
    """Update a role mapping.

    Args:
        mapping_id: Role mapping UUID
        request_data: Updated mapping configuration
        admin: Authenticated admin user

    Returns:
        Updated role mapping data

    Raises:
        HTTPException: If mapping not found or conflict
    """
    mapping = _role_mappings.get(mapping_id)
    if not mapping:
        raise HTTPException(
            status_code=404,
            detail=f"Role mapping '{mapping_id}' not found.",
        )

    # Check for duplicate if idp_group is being updated
    if request_data.idp_group:
        for mid, m in _role_mappings.items():
            if (
                mid != mapping_id
                and m["provider_id"] == mapping["provider_id"]
                and m["idp_group"].lower() == request_data.idp_group.lower()
            ):
                raise HTTPException(
                    status_code=409,
                    detail=f"Mapping for group '{request_data.idp_group}' already exists for this provider.",
                )

    # Update fields if provided
    update_data = request_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            mapping[field] = value

    # Update timestamp
    mapping["updated_at"] = datetime.now(timezone.utc).isoformat()

    logger.info(
        "Role mapping updated",
        extra={
            "mapping_id": mapping_id,
            "updated_fields": list(update_data.keys()),
            "admin_id": admin.get("id"),
            "constitutional_hash": CONSTITUTIONAL_HASH,
        },
    )

    return RoleMappingResponse(
        id=mapping["id"],
        provider_id=mapping["provider_id"],
        idp_group=mapping["idp_group"],
        acgs_role=mapping["acgs_role"],
        priority=mapping["priority"],
        description=mapping["description"],
        created_at=mapping["created_at"],
        updated_at=mapping["updated_at"],
    )


@router.delete("/role-mappings/{mapping_id}", status_code=204)
async def delete_role_mapping(
    mapping_id: str,
    admin: dict[str, Any] = Depends(get_current_admin),
) -> None:
    """Delete a role mapping.

    Args:
        mapping_id: Role mapping UUID
        admin: Authenticated admin user

    Raises:
        HTTPException: If mapping not found
    """
    if mapping_id not in _role_mappings:
        raise HTTPException(
            status_code=404,
            detail=f"Role mapping '{mapping_id}' not found.",
        )

    mapping = _role_mappings[mapping_id]
    del _role_mappings[mapping_id]

    logger.info(
        "Role mapping deleted",
        extra={
            "mapping_id": mapping_id,
            "provider_id": mapping["provider_id"],
            "idp_group": mapping["idp_group"],
            "acgs_role": mapping["acgs_role"],
            "admin_id": admin.get("id"),
            "constitutional_hash": CONSTITUTIONAL_HASH,
        },
    )
