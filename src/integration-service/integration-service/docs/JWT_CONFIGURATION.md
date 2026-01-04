# JWT Configuration for Integration Service

## Overview

The integration service uses JWT (JSON Web Token) based authentication from the shared `acgs2-core/shared/security/auth.py` module. This authentication secures the policy validation API endpoints.

## Required Environment Variables

### JWT_SECRET (Required)

The secret key used to sign and verify JWT tokens.

**Environment Variable:** `JWT_SECRET`

**How to Generate:**
```bash
# Generate a secure random secret
openssl rand -base64 32
```

**Example:**
```bash
JWT_SECRET=your-generated-secret-key-here
```

**Security Notes:**
- NEVER commit the actual JWT_SECRET to version control
- Use different secrets for development, staging, and production
- Store production secrets in a secure secrets manager (e.g., HashiCorp Vault, AWS Secrets Manager)
- Rotate secrets periodically

### JWT_PUBLIC_KEY (Optional)

Public key for asymmetric JWT verification. Only needed if using asymmetric key algorithms (RS256, ES256, etc.).

**Environment Variable:** `JWT_PUBLIC_KEY`

**Default:** `SYSTEM_PUBLIC_KEY_PLACEHOLDER`

## Configuration in Integration Service

The integration service accesses JWT configuration through the shared config module:

```python
from shared.config import settings

# JWT secret is available at:
jwt_secret = settings.security.jwt_secret.get_secret_value()

# Public key is available at:
jwt_public_key = settings.security.jwt_public_key
```

## Production Requirements

When `APP_ENV=production`, the following JWT settings are **mandatory**:
- `JWT_SECRET` must be set and cannot be a placeholder value
- `JWT_PUBLIC_KEY` must be configured (not `SYSTEM_PUBLIC_KEY_PLACEHOLDER`)

The application will fail to start in production if these requirements are not met.

## Development Setup

For development and testing:

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Generate a development JWT secret:
   ```bash
   openssl rand -base64 32
   ```

3. Update the `JWT_SECRET` in `.env` with the generated value

4. Start the service:
   ```bash
   python -m uvicorn src.main:app --reload
   ```

## Testing

The integration service includes tests to verify JWT configuration:

- `tests/test_shared_import.py::test_jwt_configuration_accessible` - Verifies JWT config from shared module
- `tests/test_shared_import.py::test_create_test_token` - Verifies token creation works

Run tests with:
```bash
JWT_SECRET=test-secret pytest tests/test_shared_import.py
```

## How JWT Authentication Works

1. **Token Creation**: Authentication service creates JWT tokens with user claims (user_id, tenant_id, roles, permissions)

2. **Token Verification**: Protected endpoints use `get_current_user` dependency to verify tokens

3. **Request Flow**:
   ```
   Client Request → Bearer Token → JWT Verification → User Claims → Endpoint Handler
   ```

4. **Security Features**:
   - Token expiration (configurable via `JWT_EXPIRATION_HOURS`)
   - Issuer validation (must be "acgs2")
   - HMAC-SHA256 signing algorithm
   - Tenant isolation enforcement

## Integration with Policy Validation Endpoints

The policy validation endpoints will require JWT authentication:

- `POST /api/policy/validate` - Validate resources against policies
- `GET /api/policy/policies` - List available policies
- `GET /api/policy/policies/{policy_id}` - Get specific policy
- `GET /api/policy/health` - Health check endpoint

All requests must include a valid Bearer token:
```bash
curl -H "Authorization: Bearer <jwt-token>" \
     https://api.example.com/api/policy/validate
```

## Troubleshooting

### "JWT_SECRET not configured" Error

**Cause:** JWT_SECRET environment variable is not set

**Solution:** Set the JWT_SECRET environment variable before starting the service

### "Invalid authentication token" Error

**Cause:** Token is expired, malformed, or signed with wrong secret

**Solution:**
- Verify JWT_SECRET matches between token issuer and verifier
- Check token expiration time
- Ensure token format is valid (three dot-separated parts)

### Production Startup Failure

**Cause:** JWT_SECRET or JWT_PUBLIC_KEY not properly configured for production

**Solution:** Ensure all required production security settings are configured in your production environment

## References

- Shared Auth Module: `acgs2-core/shared/security/auth.py`
- Shared Config Module: `acgs2-core/shared/config.py`
- Environment Template: `integration-service/.env.example`
