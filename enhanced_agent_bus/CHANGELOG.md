# Changelog

<!-- Constitutional Hash: cdd01ef066bc6cf2 -->

All notable changes to the Enhanced Agent Bus are documented in this file.

## [1.1.0] - 2025-12-21

### Added

- **S3/MinIO Storage Integration**: Full cloud storage support in `storage_service.py`
  - Automatic fallback to local filesystem when S3 unavailable
  - MinIO endpoint support via `S3_ENDPOINT_URL` environment variable
  - Constitutional hash metadata in S3 object tags
  - `bundle_exists()` method for checking bundle availability

- **Authorization Caching**: Performance optimization in `opa_service.py`
  - 15-minute TTL cache for RBAC authorization decisions
  - Role-based caching (not user-specific) for better hit rates
  - Automatic cache cleanup for expired entries
  - `invalidate_cache()` method for manual cache clearing

- **Policy Version Caching**: Faster lookups in `policy_service.py`
  - Active version caching with 1-hour TTL
  - Automatic cache invalidation on version activation
  - Integrated with existing cache service

### Changed

- **Logging Migration**: Replaced `print()` with proper logging
  - `impact_scorer.py`: ONNX model loading → `logger.info()`
  - `impact_scorer.py`: AI model failure → `logger.warning()`
  - `hitl_manager.py`: Mock audit → `logger.debug()`
  - `hitl_manager.py`: Initialization → `logger.info()`

- **Exception Handling**: Replaced bare `except:` with specific types
  - `health_check_endpoints.py`: `ValueError`, `TypeError`, `aiohttp.ContentTypeError`
  - `retrieval_engine.py`: `ValueError`, `TypeError`, `AttributeError`
  - `constraint_generator.py`: `KeyError`, `IndexError`, `TypeError`
  - `notification_service.py`: `asyncio.QueueFull`, `RuntimeError`, `AttributeError`

### Security

- Added security documentation comments for `exec()` usage in test files
- Verified secrets management uses environment variables (no hardcoded secrets)

### Documentation

- Updated README.md with v1.1.0 release notes
- Added "Recent Updates" section documenting improvements
- Enhanced contributing guidelines with code quality standards
- Created CHANGELOG.md for version tracking

## [1.0.0] - 2025-12-17

### Initial Release

- Core message bus implementation with Python/Rust backends
- Constitutional validation with hash `cdd01ef066bc6cf2`
- OPA policy integration
- Policy registry client
- Deliberation layer for AI-powered review
- Circuit breaker patterns
- Prometheus metrics integration
- 515 tests with 63.99% coverage
- P99 latency: 0.023ms
- Throughput: 55,978 RPS

---

*Constitutional Hash: cdd01ef066bc6cf2*
