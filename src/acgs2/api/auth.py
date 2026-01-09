"""
ACGS-2 Authentication Middleware

Provides JWT token validation, API key authentication, and rate limiting
for the FastAPI application.
"""

import hashlib
import logging
import os
import secrets
import time
import warnings
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# =============================================================================
# Configuration
# =============================================================================

# JWT settings
JWT_SECRET_KEY = os.environ.get("ACGS2_JWT_SECRET")
if not JWT_SECRET_KEY:
    warnings.warn(
        "ACGS2_JWT_SECRET not set; using insecure default for development only",
        UserWarning,
        stacklevel=2,
    )
    JWT_SECRET_KEY = "dev-only-insecure-key"
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Rate limiting settings
RATE_LIMIT_REQUESTS = 100  # requests per window
RATE_LIMIT_WINDOW_SECONDS = 3600  # 1 hour window

# API Key settings
API_KEY_LENGTH = 32

# =============================================================================
# Data Models
# =============================================================================


class User(BaseModel):
    """User model for authentication."""

    user_id: str
    username: str
    role: str  # "user" or "admin"
    created_at: str
    last_login: Optional[str] = None


class TokenData(BaseModel):
    """Data stored in JWT tokens."""

    user_id: str
    username: str
    role: str
    exp: int


class LoginRequest(BaseModel):
    """Login request model."""

    username: str
    password: str  # In production, use proper password hashing


class LoginResponse(BaseModel):
    """Login response model."""

    access_token: str
    token_type: str = "bearer"
    user: User


class APIKeyCreateRequest(BaseModel):
    """API key creation request."""

    name: str
    role: str = "user"


class APIKeyResponse(BaseModel):
    """API key creation response."""

    api_key: str
    name: str
    role: str
    created_at: str


# =============================================================================
# Authentication Manager
# =============================================================================


class AuthManager:
    """Manages authentication, authorization, and rate limiting."""

    def __init__(self):
        # User store (in production, use database)
        self.users: Dict[str, User] = {}

        # API key store: key_hash -> (user_id, role, name, created_at)
        self.api_keys: Dict[str, Tuple[str, str, str, str]] = {}

        # Rate limiting: user_id -> [timestamps of requests in window]
        self.rate_limit_data: Dict[str, list] = {}

        # Session tracking for rate limiting
        self._cleanup_old_requests()

        logger.info("AuthManager initialized")

    def create_user(self, username: str, password: str, role: str = "user") -> User:
        """Create a new user."""
        user_id = f"user_{len(self.users) + 1}"
        user = User(
            user_id=user_id,
            username=username,
            role=role,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self.users[user_id] = user
        logger.info(f"Created user: {username} ({role})")
        return user

    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user with username/password."""
        # In production, verify password hash
        for user in self.users.values():
            if user.username == username:
                # Mock password check - in production use proper verification
                if password == f"password_for_{username}":
                    user.last_login = datetime.now(timezone.utc).isoformat()
                    return user
        return None

    def create_access_token(self, user: User) -> str:
        """Create JWT access token for user."""
        expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
        to_encode = TokenData(
            user_id=user.user_id,
            username=user.username,
            role=user.role,
            exp=int(expire.timestamp()),
        ).dict()

        encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        return encoded_jwt

    def verify_token(self, token: str) -> Optional[User]:
        """Verify JWT token and return user."""
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            token_data = TokenData(**payload)

            # Check expiration
            if datetime.fromtimestamp(token_data.exp, timezone.utc) < datetime.now(timezone.utc):
                return None

            return self.users.get(token_data.user_id)
        except jwt.PyJWTError:
            return None

    def create_api_key(self, user_id: str, name: str, role: str = "user") -> str:
        """Create a new API key for a user."""
        # Generate secure random key
        api_key = secrets.token_hex(API_KEY_LENGTH)

        # Hash the key for storage (we store hash, return actual key)
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        created_at = datetime.now(timezone.utc).isoformat()
        self.api_keys[key_hash] = (user_id, role, name, created_at)

        logger.info(f"Created API key for user {user_id}: {name}")
        return api_key

    def verify_api_key(self, api_key: str) -> Optional[User]:
        """Verify API key and return associated user."""
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        if key_hash not in self.api_keys:
            return None

        user_id, role, name, created_at = self.api_keys[key_hash]

        # Create user object for API key (no username for API keys)
        return User(user_id=user_id, username=f"api_key_{name}", role=role, created_at=created_at)

    def check_rate_limit(self, user_id: str) -> bool:
        """
        Check if user is within rate limits.

        Returns True if request is allowed, False if rate limited.
        """
        now = time.time()
        window_start = now - RATE_LIMIT_WINDOW_SECONDS

        if user_id not in self.rate_limit_data:
            self.rate_limit_data[user_id] = []

        # Clean old requests
        self.rate_limit_data[user_id] = [
            req_time for req_time in self.rate_limit_data[user_id] if req_time > window_start
        ]

        # Check if under limit
        if len(self.rate_limit_data[user_id]) >= RATE_LIMIT_REQUESTS:
            return False

        # Add current request
        self.rate_limit_data[user_id].append(now)
        return True

    def get_rate_limit_info(self, user_id: str) -> Dict[str, Any]:
        """Get rate limiting information for user."""
        if user_id not in self.rate_limit_data:
            return {
                "requests_used": 0,
                "requests_limit": RATE_LIMIT_REQUESTS,
                "window_seconds": RATE_LIMIT_WINDOW_SECONDS,
                "reset_in_seconds": RATE_LIMIT_WINDOW_SECONDS,
            }

        now = time.time()
        window_start = now - RATE_LIMIT_WINDOW_SECONDS

        # Clean and count
        valid_requests = [
            req_time for req_time in self.rate_limit_data[user_id] if req_time > window_start
        ]
        self.rate_limit_data[user_id] = valid_requests

        # Calculate reset time
        if valid_requests:
            oldest_request = min(valid_requests)
            reset_in = int((oldest_request + RATE_LIMIT_WINDOW_SECONDS) - now)
        else:
            reset_in = RATE_LIMIT_WINDOW_SECONDS

        return {
            "requests_used": len(valid_requests),
            "requests_limit": RATE_LIMIT_REQUESTS,
            "window_seconds": RATE_LIMIT_WINDOW_SECONDS,
            "reset_in_seconds": max(0, reset_in),
        }

    def _cleanup_old_requests(self):
        """Clean up old rate limiting data."""
        # This would be called periodically in a real system
        now = time.time()
        window_start = now - RATE_LIMIT_WINDOW_SECONDS

        for user_id in list(self.rate_limit_data.keys()):
            self.rate_limit_data[user_id] = [
                req_time for req_time in self.rate_limit_data[user_id] if req_time > window_start
            ]
            # Remove empty entries
            if not self.rate_limit_data[user_id]:
                del self.rate_limit_data[user_id]


# =============================================================================
# Global Auth Manager Instance
# =============================================================================

auth_manager = AuthManager()

# Initialize with test users and API keys only in dev mode
if os.environ.get("ACGS2_DEV_MODE", "").lower() in ("true", "1", "yes"):
    test_user = auth_manager.create_user("testuser", "password_for_testuser", "user")
    admin_user = auth_manager.create_user("admin", "password_for_admin", "admin")

    # Create API keys for testing
    test_api_key = auth_manager.create_api_key(test_user.user_id, "test_key", "user")
    admin_api_key = auth_manager.create_api_key(admin_user.user_id, "admin_key", "admin")

    logger.info("Dev mode: Test users and API keys created (not printed for security)")

# =============================================================================
# FastAPI Dependencies
# =============================================================================

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security), request: Request = None
) -> User:
    """
    Dependency to get current authenticated user.

    Supports both JWT tokens and API keys.
    """
    if not credentials:
        # Check for API key in headers
        api_key = request.headers.get("X-API-Key") if request else None
        if api_key:
            user = auth_manager.verify_api_key(api_key)
            if user:
                return user
        raise HTTPException(status_code=401, detail="Authentication required")

    token = credentials.credentials

    # Try JWT first
    user = auth_manager.verify_token(token)
    if user:
        return user

    # Try API key
    user = auth_manager.verify_api_key(token)
    if user:
        return user

    raise HTTPException(status_code=401, detail="Invalid authentication credentials")


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security), request: Request = None
) -> Optional[User]:
    """
    Optional authentication - returns user if authenticated, None otherwise.
    """
    try:
        return await get_current_user(credentials, request)
    except HTTPException:
        return None


async def require_admin(user: User = Depends(get_current_user)) -> User:
    """Require admin role."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


async def check_rate_limit(user: User = Depends(get_current_user_optional)) -> User:
    """Check rate limiting for authenticated requests."""
    if user:
        user_id = user.user_id
    else:
        # Anonymous requests - use IP-based limiting (simplified)
        user_id = "anonymous"

    if not auth_manager.check_rate_limit(user_id):
        # Get rate limit info for error message
        limit_info = auth_manager.get_rate_limit_info(user_id)
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={
                "X-RateLimit-Limit": str(limit_info["requests_limit"]),
                "X-RateLimit-Remaining": str(
                    limit_info["requests_limit"] - limit_info["requests_used"]
                ),
                "X-RateLimit-Reset": str(int(time.time()) + limit_info["reset_in_seconds"]),
            },
        )

    return user


# Authentication Routes
# =============================================================================

auth_router = APIRouter(prefix="/auth", tags=["authentication"])


@auth_router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Authenticate user and return access token."""
    user = auth_manager.authenticate_user(request.username, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = auth_manager.create_access_token(user)

    return LoginResponse(access_token=access_token, token_type="bearer", user=user)


@auth_router.post("/api-keys", response_model=APIKeyResponse)
async def create_api_key(request: APIKeyCreateRequest, user: User = Depends(get_current_user)):
    """Create a new API key for the authenticated user."""
    api_key = auth_manager.create_api_key(user.user_id, request.name, request.role)

    return APIKeyResponse(
        api_key=api_key,
        name=request.name,
        role=request.role,
        created_at=datetime.now(timezone.utc).isoformat(),
    )


@auth_router.get("/me")
async def get_current_user_info(user: User = Depends(get_current_user)):
    """Get current user information."""
    return user


@auth_router.get("/rate-limit")
async def get_rate_limit_info(user: User = Depends(get_current_user_optional)):
    """Get rate limiting information for current user."""
    if user:
        user_id = user.user_id
    else:
        user_id = "anonymous"

    return auth_manager.get_rate_limit_info(user_id)


# =============================================================================
# Middleware Function
# =============================================================================


async def auth_middleware(request: Request, call_next):
    """
    Authentication middleware for FastAPI.

    This can be added to the app.middleware stack if needed.
    """
    # Skip auth for certain paths
    skip_auth_paths = ["/docs", "/redoc", "/openapi.json", "/auth/login"]

    if request.url.path in skip_auth_paths:
        return await call_next(request)

    # For API routes, require authentication
    if request.url.path.startswith("/api/"):
        try:
            await get_current_user(None, request)
        except HTTPException as exc:
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    response = await call_next(request)
    return response
