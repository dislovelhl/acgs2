# Assets Directory

This directory contains static assets, data files, and project metadata for the ACGS-2 project.

## Contents

### Project Metadata
- `PROJECT_INDEX.json` - Comprehensive project index in JSON format
- `PROJECT_INDEX.md` - Human-readable project index and documentation

### Audit & Compliance Data
- `audit_anchor_production.json` - Production audit anchor data

### Logs & Debug Files
- `firebase-debug.log` - Firebase debugging logs
- `performance_monitor.log` - Performance monitoring logs

### Visual Assets
- `import_graph.png` - Import dependency visualization

### Code Assets
- `neural_training_demo.js` - Neural network training demonstration

## Usage

### Project Index
The project index files provide comprehensive information about:
- Project structure and components
- File locations and descriptions
- Development tools and utilities
- Quality assurance metrics

```bash
# View project structure
cat assets/PROJECT_INDEX.md

# Parse JSON index programmatically
python -c "import json; print(json.load(open('assets/PROJECT_INDEX.json')))"
```

### Audit Data
Audit anchor files are used for:
- Blockchain-anchored audit trails
- Compliance verification
- Constitutional governance validation

### Log Files
Log files contain debugging and monitoring information:
- Firebase logs for integration debugging
- Performance logs for system monitoring

## Constitutional Compliance

**Constitutional Hash**: `cdd01ef066bc6cf2`

Assets must support constitutional compliance and governance requirements.

## Maintenance

### File Management
- Regularly review and clean up old log files
- Update project index files as project structure changes
- Archive audit data for compliance retention

### Backup Strategy
- Critical assets (audit data, project index) should be backed up
- Log files can be archived quarterly
- Visual assets should be version controlled

### Security Considerations
- Audit data contains sensitive compliance information
- Log files may contain debugging information
- Access controls should be applied as appropriate

## File Naming Convention

- Use descriptive names with clear purpose indication
- Include timestamps for log files when applicable
- Use consistent file extensions (.json, .md, .log, .png, .js)
- Avoid generic names like "data.json" or "file.txt"
