# ACGS-2 CLI Tool

**Constitutional Hash:** `cdd01ef066bc6cf2`

A comprehensive command-line interface for the AI Constitutional Governance System (ACGS-2). Provides unified access to all platform services including HITL Approvals, ML Governance, Policy Management, and an interactive Policy Playground.

## Installation

```bash
# Install from source
pip install -e ./tools/acgs2-cli

# Or install the SDK first
pip install acgs2-sdk
pip install -e ./tools/acgs2-cli
```

## Quick Start

```bash
# Check system health
acgs2-cli health

# Create an approval request
acgs2-cli hitl create --type model_deployment --payload '{"model": "v2", "env": "prod"}'

# List ML models
acgs2-cli ml models list

# Start interactive policy playground
acgs2-cli playground --interactive

# Validate a policy
acgs2-cli policy validate policy-123 --context '{"action": "deploy"}'
```

## Configuration

The CLI can be configured via command-line options or a config file at `~/.acgs2/config.json`:

```json
{
  "base_url": "http://localhost:8080",
  "tenant_id": "acgs-dev",
  "timeout": 30.0
}
```

## Commands

### Core Commands

- `health` - Check ACGS-2 system health
- `version` - Show CLI version and constitutional hash

### HITL Approvals (`hitl`)

```bash
# Create approval request
acgs2-cli hitl create --type model_deployment --payload-file deployment.json --risk-score 75

# List requests
acgs2-cli hitl list --status pending --limit 10

# Show request details
acgs2-cli hitl show req-123

# Submit decision
acgs2-cli hitl decide req-123 --decision approve --reasoning "Meets requirements"

# Escalate request
acgs2-cli hitl escalate req-123 --reason "Urgent deployment needed"

# View pending approvals for user
acgs2-cli hitl pending alice@example.com
```

### ML Governance (`ml`)

```bash
# Models
acgs2-cli ml models create --name fraud-model --framework scikit-learn --model-type classification
acgs2-cli ml models list --limit 20
acgs2-cli ml models show model-123
acgs2-cli ml models update model-123 --accuracy 0.92
acgs2-cli ml models drift model-123

# Predictions
acgs2-cli ml predict model-123 --features '{"amount": 150, "category": "online"}' --confidence

# Feedback
acgs2-cli ml feedback model-123 --prediction-id pred-456 --type correction --value false

# A/B Tests
acgs2-cli ml abtests create --name comparison --model-a model-1 --model-b model-2 --duration 14
acgs2-cli ml abtests list
acgs2-cli ml abtests results test-123
```

### Policy Management (`policy`)

```bash
# Create policy
acgs2-cli policy create --name "Data Privacy" --file policy.json --tags "gdpr,privacy"

# List policies
acgs2-cli policy list --status active --limit 10

# Show policy
acgs2-cli policy show policy-123

# Update policy
acgs2-cli policy update policy-123 --status active

# Validate compliance
acgs2-cli policy validate policy-123 --context '{"user": "alice", "action": "read"}'

# Test policy (creates temporary policy)
acgs2-cli policy test my-policy.json --context-file test-context.json
```

### Policy Playground (`playground`)

Interactive mode for experimenting with policies:

```bash
# Start interactive playground
acgs2-cli playground --interactive

# Load policy and context for single validation
acgs2-cli playground --policy my-policy.json --context '{"action": "deploy"}'
```

#### Playground Commands

```
playground> help                    # Show help
playground> load policy.json        # Load policy from file
playground> context {"action": "read"}  # Set context
playground> validate                # Run validation
playground> show-policy             # Display current policy
playground> show-context            # Display current context
playground> quit                    # Exit
```

## Examples

### Complete Workflow Example

```bash
# 1. Check system health
acgs2-cli health

# 2. Create a policy for model deployment approval
cat > deployment-policy.json << 'EOF'
[
  {
    "id": "risk_check",
    "condition": "data.risk_score > 70",
    "action": "require_approval"
  }
]
EOF

acgs2-cli policy create --name "Model Deployment" --file deployment-policy.json

# 3. Register a new ML model
acgs2-cli ml models create --name fraud-detector --framework tensorflow --model-type classification

# 4. Create approval request for production deployment
acgs2-cli hitl create --type model_deployment --payload '{
  "model_id": "fraud-detector",
  "environment": "production",
  "risk_score": 75,
  "performance_metrics": {
    "accuracy": 0.94,
    "precision": 0.91
  }
}' --risk-score 75

# 5. List pending approvals
acgs2-cli hitl list --status pending

# 6. Approve the request
acgs2-cli hitl decide req-123 --decision approve --reasoning "Performance metrics excellent"
```

## Development

```bash
# Install in development mode
pip install -e ./tools/acgs2-cli

# Run tests
pytest

# Run linting
ruff check acgs2_cli/
mypy acgs2_cli/
```

## Constitutional Compliance

All CLI operations are constitutionally compliant with hash `cdd01ef066bc6cf2`. The CLI automatically includes constitutional validation in all API requests and provides clear feedback on compliance status.

## Support

- **Documentation**: https://docs.acgs.io/cli
- **Issues**: https://github.com/acgs/acgs2/issues
- **Constitutional Hash**: `cdd01ef066bc6cf2`
