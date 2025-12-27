# Documentation Specialist Mode - ACGS-2 Project

## Mode-Specific Guidelines for ACGS-2 Documentation

### Constitutional Compliance Documentation
- **Always reference constitutional hash**: `cdd01ef066bc6cf2` in all documentation
- **Document validation requirements**: Explain hash validation in API docs and guides
- **Security-first approach**: Lead with security and compliance information

### Architecture Documentation Standards
- **Multi-backend explanation**: Clearly distinguish Python vs Rust implementations
- **Fallback mechanisms**: Document graceful degradation (Rust → Python, Dynamic → Static)
- **Performance trade-offs**: Explain when to use each backend option

### Deliberation Layer Documentation
- **Impact scoring**: Document the 0.0-1.0 risk assessment system
- **Threshold explanations**: Explain default 0.8 threshold and adaptive learning
- **Human-in-the-loop**: Document AI-assisted decision making processes

### Multi-tenant Documentation
- **Tenant isolation**: Explain `tenant_id` segregation in all messaging operations
- **Security contexts**: Document additional security metadata requirements
- **Agent registration**: Emphasize pre-registration requirements

### Custom Tool Documentation
- **Syntax repair tools**: Document usage of `tools/` utilities for code fixes
- **Deployment scripts**: Explain blue-green deployment and rollback procedures
- **Testing infrastructure**: Document custom test markers and performance testing

### Code Example Standards
- **Constitutional hash inclusion**: All code examples must include `constitutional_hash="cdd01ef066bc6cf2"`
- **Error handling**: Show proper exception handling with fallbacks
- **Async patterns**: Demonstrate comprehensive async/await usage
- **Type hints**: Include proper type annotations in examples

### Security Documentation Requirements
- **Validation failures**: Document consequences of hash mismatches
- **Dynamic policy**: Explain optional policy registry integration
- **Audit trails**: Document compliance logging and verification

### Performance Documentation
- **Metrics collection**: Document built-in performance monitoring
- **Connection pooling**: Explain Redis connection management
- **Caching strategies**: Document agent registry and routing caches

### Troubleshooting Documentation
- **Common issues**: Document constitutional hash mismatches, Rust backend failures
- **Debug modes**: Show logging configuration for troubleshooting
- **Health checks**: Document system health verification procedures

### Integration Documentation
- **External services**: Document Redis, policy registry, search platform integration
- **API compatibility**: Explain fallback imports and optional dependencies
- **Version constraints**: Document strict dependency versioning

### Documentation Structure
- **User guides**: Comprehensive guides in `docs/user-guides/`
- **API references**: Complete API documentation with examples
- **Troubleshooting**: Dedicated troubleshooting sections
- **Deployment guides**: Kubernetes and Docker deployment instructions

### Quality Standards
- **Clarity**: Explain complex concepts simply and comprehensively
- **Consistency**: Maintain consistent tone and formatting
- **Completeness**: Include all project-specific non-obvious information
- **Accuracy**: Ensure all technical details are correct and up-to-date

### Link Validation
- **Broken links**: Always check and fix broken internal/external links
- **Cross-references**: Ensure proper linking between related documents
- **Navigation**: Provide clear table of contents and navigation aids

### Formatting Standards
- **Markdown syntax**: Use proper markdown formatting throughout
- **Code blocks**: Include syntax highlighting and clear examples
- **Tables**: Use tables for structured information (message types, priorities, etc.)
- **Lists**: Use consistent bullet and numbered list formatting