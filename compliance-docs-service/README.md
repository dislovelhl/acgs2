# Compliance Docs Service

Service for generating compliance documentation and evidence exports for ACGS-2.

## Features
- SOC 2 Type II control mapping
- ISO 27001 Annex A evidence
- GDPR Article 30 records
- EU AI Act risk classification
- Automated evidence export (PDF, DOCX, XLSX)

## Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run service
uvicorn src.main:app --reload --host 0.0.0.0 --port 8100
```

## Testing

```bash
pytest
```
