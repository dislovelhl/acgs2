# ACGS-2 API Specifications

> Constitutional Hash: cdd01ef066bc6cf2
> Generated: 2025-12-30

This directory contains OpenAPI 3.0 specifications for all ACGS-2 container APIs.

## API Index

| API | File | Port | Description |
|-----|------|------|-------------|
| Policy Registry | [policy-registry-api.yaml](./policy-registry-api.yaml) | 8000 | Dynamic policy management with Ed25519 signatures |
| Audit Service | [audit-service-api.yaml](./audit-service-api.yaml) | 8084 | Immutable audit trails with blockchain anchoring |

## Usage

### View in Swagger UI

```bash
# Using docker
docker run -p 8080:8080 -e SWAGGER_JSON=/api/policy-registry-api.yaml \
  -v $(pwd):/api swaggerapi/swagger-ui

# Using npx
npx swagger-ui-watcher policy-registry-api.yaml
```

### Generate Client SDK

```bash
# Python client
openapi-generator generate -i policy-registry-api.yaml -g python -o ./sdk/python

# TypeScript client
openapi-generator generate -i policy-registry-api.yaml -g typescript-axios -o ./sdk/typescript
```

### Validate Specifications

```bash
# Using spectral
npx @stoplight/spectral-cli lint *.yaml

# Using openapi-generator
openapi-generator validate -i policy-registry-api.yaml
```

## API Standards

All APIs follow these standards:

### Authentication

- **External Clients:** JWT Bearer tokens via `/auth/login`
- **Internal Services:** `X-Internal-API-Key` header
- **Constitutional Hash:** `cdd01ef066bc6cf2` required in relevant operations

### Common Headers

| Header | Required | Description |
|--------|----------|-------------|
| `Authorization` | Yes (external) | Bearer token |
| `X-Internal-API-Key` | Yes (internal) | Service API key |
| `X-Request-ID` | Recommended | Request correlation ID |
| `X-Constitutional-Hash` | Conditional | Constitutional hash for governance operations |

### Response Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 429 | Too Many Requests |
| 500 | Internal Server Error |

### Error Response Format

```json
{
  "detail": "Error description",
  "error_code": "ERROR_CODE",
  "timestamp": "2025-12-30T12:00:00Z"
}
```

## Container API Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        ACGS-2 Platform                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    │
│   │   Policy     │    │    Audit     │    │     OPA      │    │
│   │  Registry    │    │   Ledger     │    │   Sidecar    │    │
│   │   :8000      │    │   :8084      │    │   :8181      │    │
│   └──────────────┘    └──────────────┘    └──────────────┘    │
│          │                   │                   │             │
│          └───────────────────┴───────────────────┘             │
│                              │                                  │
│                    ┌─────────┴─────────┐                       │
│                    │  Enhanced Agent   │                       │
│                    │       Bus         │                       │
│                    │   (Internal)      │                       │
│                    └───────────────────┘                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Related Documentation

- [C4 Container Documentation](../c4-container.md) - Full container architecture
- [C4 Component Documentation](../c4-component.md) - Component breakdown
- [C4 Code Documentation](../c4-code-core.md) - Code-level details

---

*Constitutional Hash: cdd01ef066bc6cf2*
