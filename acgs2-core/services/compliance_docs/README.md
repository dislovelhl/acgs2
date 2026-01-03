# ACGS-2 Compliance Documentation Service

**Constitutional Hash**: `cdd01ef066bc6cf2`

## Overview

The Compliance Documentation Service generates, manages, and serves compliance documentation for the ACGS-2 platform. It creates audit reports, regulatory filings, and compliance certificates in multiple formats (PDF, DOCX, XLSX) for various regulatory frameworks.

## Architecture

The service implements a document generation pipeline with the following components:

- **Template Engine**: Jinja2-based template rendering
- **Document Generators**: Multi-format document creation (PDF, Word, Excel)
- **Data Sources**: Integration with audit logs, agent metrics, and compliance data
- **Storage**: Document versioning and archival
- **API**: RESTful endpoints for document generation and retrieval

## Supported Frameworks

### AI Regulations
- **EU AI Act**: Technical documentation and conformity assessments
- **NIST AI RMF**: AI risk management framework documentation
- **ISO/IEC 42001**: AI management system documentation

### Data Protection
- **GDPR**: Data processing records and privacy impact assessments
- **CCPA**: California Consumer Privacy Act compliance reports

### Industry Standards
- **SOX**: Sarbanes-Oxley compliance documentation
- **PCI DSS**: Payment card industry compliance reports

## API Endpoints

### Document Generation
- `POST /api/v1/documents/generate` - Generate compliance document
- `POST /api/v1/documents/batch` - Generate multiple documents
- `GET /api/v1/documents/templates` - List available templates

### Document Management
- `GET /api/v1/documents/{id}` - Retrieve document
- `GET /api/v1/documents/{id}/download` - Download document
- `DELETE /api/v1/documents/{id}` - Delete document
- `GET /api/v1/documents` - List documents with filtering

### Templates
- `GET /api/v1/templates` - List available templates
- `POST /api/v1/templates` - Create custom template
- `PUT /api/v1/templates/{id}` - Update template
- `DELETE /api/v1/templates/{id}` - Delete template

### Health Checks
- `GET /health` - Service health status
- `GET /health/live` - Kubernetes liveness probe
- `GET /health/ready` - Kubernetes readiness probe

## Document Types

### Audit Reports
- **System Audits**: Complete platform audit trails
- **Agent Activity Reports**: AI agent decision documentation
- **Security Assessments**: Vulnerability and penetration test reports

### Compliance Certificates
- **Conformity Declarations**: EU AI Act compliance certificates
- **Risk Assessments**: AI system risk evaluation reports
- **Data Processing Records**: GDPR Article 30 records

### Regulatory Filings
- **Incident Reports**: Security breach documentation
- **Annual Reports**: Regulatory compliance summaries
- **Change Management**: System modification documentation

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `COMPLIANCE_DOCS_PORT` | `8100` | Port to listen on |
| `AUDIT_SERVICE_URL` | `http://localhost:8300` | Audit service URL |
| `TENANT_MANAGEMENT_URL` | `http://localhost:8500` | Tenant management URL |
| `DOCUMENT_STORAGE_PATH` | `./documents` | Document storage directory |
| `TEMPLATE_PATH` | `./templates` | Template directory |
| `MAX_DOCUMENT_SIZE` | `50MB` | Maximum document size |
| `RETENTION_DAYS` | `2555` | Document retention period (7 years) |

### Template Configuration

Templates are stored in the `templates/` directory with the following structure:

```
templates/
├── eu_ai_act/
│   ├── technical_documentation.j2
│   └── conformity_assessment.j2
├── gdpr/
│   ├── dpa_template.j2
│   └── privacy_impact.j2
└── nist/
    ├── risk_assessment.j2
    └── system_documentation.j2
```

## Development

### Local Development Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run with auto-reload
uvicorn src.main:app --reload --port 8100

# Run tests
pytest tests/
```

### Docker Development

```bash
# Build and run
docker build -f Dockerfile.dev -t acgs2-compliance-docs .
docker run -p 8100:8100 -v ./documents:/app/documents acgs2-compliance-docs
```

## Deployment

### Docker Compose

```yaml
compliance-docs:
  build:
    context: ./services/compliance_docs
    dockerfile: Dockerfile.dev
  ports:
    - "8100:8100"
  volumes:
    - ./documents:/app/documents
    - ./templates:/app/templates
  environment:
    - COMPLIANCE_DOCS_PORT=8100
    - AUDIT_SERVICE_URL=http://audit-service:8300
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: compliance-docs
spec:
  replicas: 2
  selector:
    matchLabels:
      app: compliance-docs
  template:
    metadata:
      labels:
        app: compliance-docs
    spec:
      containers:
      - name: compliance-docs
        image: acgs2/compliance-docs:latest
        ports:
        - containerPort: 8100
        volumeMounts:
        - name: documents
          mountPath: /app/documents
        - name: templates
          mountPath: /app/templates
        env:
        - name: COMPLIANCE_DOCS_PORT
          value: "8100"
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8100
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8100
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: documents
        persistentVolumeClaim:
          claimName: compliance-docs-pvc
      - name: templates
        configMap:
          name: compliance-templates
```

## Document Generation Process

### 1. Request Validation
- Validate input parameters and user permissions
- Check regulatory framework requirements
- Verify data source availability

### 2. Data Collection
- Query audit service for relevant logs
- Retrieve agent metrics and configurations
- Gather system and tenant information

### 3. Template Processing
- Select appropriate template for framework
- Render template with collected data
- Apply formatting and styling

### 4. Document Creation
- Generate document in requested format
- Apply digital signatures if required
- Add metadata and timestamps

### 5. Storage and Delivery
- Store document with version control
- Generate download URLs
- Send notifications if configured

## Monitoring

### Metrics

Prometheus metrics exposed at `/metrics`:

- `compliance_docs_generated_total` - Total documents generated
- `compliance_docs_generation_duration` - Document generation time
- `compliance_docs_storage_used_bytes` - Storage utilization
- `compliance_docs_errors_total` - Error count by type

### Logging

Structured logging includes:

- Document generation events
- Template rendering performance
- Storage operations
- Error conditions with context

## Security

### Access Control
- JWT-based authentication
- Role-based document access
- Tenant data isolation
- Audit logging for all operations

### Data Protection
- Encryption at rest for sensitive documents
- Secure deletion of expired documents
- Compliance with data retention regulations

## Testing

### Unit Tests

```bash
pytest tests/test_document_generation.py -v
pytest tests/test_template_rendering.py -v
pytest tests/test_api_endpoints.py -v
```

### Integration Tests

```bash
pytest tests/integration/test_full_pipeline.py -v
pytest tests/integration/test_external_services.py -v
```

## Templates

### Custom Template Development

Templates use Jinja2 syntax with custom filters:

```jinja2
# Document header
{{ document.title }}
Generated: {{ document.created_at | datetime_format }}

# Compliance section
{% for requirement in compliance_requirements %}
## {{ requirement.name }}
{{ requirement.description }}

Status: {{ requirement.status }}
Evidence: {{ requirement.evidence }}
{% endfor %}
```

### Template Variables

Available context variables:
- `document`: Document metadata
- `tenant`: Tenant information
- `audit_data`: Audit logs and events
- `compliance_data`: Framework-specific compliance data
- `system_info`: Platform configuration and metrics

## Contributing

Follow the ACGS-2 service development guidelines. When adding new regulatory frameworks:

1. Create template directory under `templates/`
2. Add framework-specific data models
3. Implement validation logic
4. Add comprehensive tests
5. Update API documentation

## License

This service is part of the ACGS-2 platform and follows the same license terms.
