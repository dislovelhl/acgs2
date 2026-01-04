# ACGS-2 Human-in-the-Loop Approvals Service

**Constitutional Hash**: `cdd01ef066bc6cf2`

## Overview

The Human-in-the-Loop (HITL) Approvals Service manages human oversight and approval workflows for high-impact AI agent decisions. It integrates with communication platforms (Slack, Teams) and provides escalation mechanisms for decisions requiring human judgment.

## Architecture

The service implements a comprehensive approval workflow system with the following components:

- **Approval Engine**: Decision routing and workflow management
- **Notification System**: Multi-platform notification delivery
- **Escalation Policies**: Configurable approval hierarchies
- **Audit Trail**: Complete approval history and decision tracking
- **Integration APIs**: REST and webhook interfaces for external systems

## Approval Types

### Decision Categories
- **High-Risk Actions**: Financial transactions, system modifications
- **Policy Violations**: Constitutional compliance escalations
- **Anomaly Detection**: Unusual agent behavior patterns
- **Regulatory Requirements**: Mandatory human oversight decisions
- **Quality Assurance**: Random sampling for quality control

### Workflow Types
- **Single Approver**: Simple yes/no decisions
- **Multi-Level Approval**: Sequential approval chains
- **Consensus Approval**: Multiple approvers required
- **Time-Based Escalation**: Automatic escalation on timeout
- **Emergency Bypass**: Critical situation fast-tracking

## API Endpoints

### Approval Management
- `POST /api/v1/approvals` - Create new approval request
- `GET /api/v1/approvals/{id}` - Get approval details
- `PUT /api/v1/approvals/{id}` - Update approval status
- `GET /api/v1/approvals` - List approvals with filtering

### Workflow Configuration
- `POST /api/v1/workflows` - Create approval workflow
- `GET /api/v1/workflows` - List available workflows
- `PUT /api/v1/workflows/{id}` - Update workflow configuration
- `DELETE /api/v1/workflows/{id}` - Delete workflow

### Notifications
- `POST /api/v1/notifications/test` - Test notification delivery
- `GET /api/v1/notifications/channels` - List available channels

### Health Checks
- `GET /health` - Service health status
- `GET /health/live` - Kubernetes liveness probe
- `GET /health/ready` - Kubernetes readiness probe

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HITL_APPROVALS_PORT` | `8200` | Port to listen on |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection URL |
| `DEFAULT_TIMEOUT` | `3600` | Default approval timeout (seconds) |
| `MAX_CONCURRENT_APPROVALS` | `100` | Maximum concurrent approvals |
| `NOTIFICATION_RETRY_ATTEMPTS` | `3` | Notification retry attempts |

### Notification Configuration

#### Slack Integration
```bash
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_SIGNING_SECRET=your-signing-secret
SLACK_DEFAULT_CHANNEL=#ai-approvals
```

#### Microsoft Teams
```bash
TEAMS_WEBHOOK_URL=https://outlook.office.com/webhook/...
TEAMS_DEFAULT_CHANNEL=AI Approvals
```

#### PagerDuty
```bash
PAGERDUTY_INTEGRATION_KEY=your-integration-key
PAGERDUTY_DEFAULT_SERVICE=ai-approvals
```

### Workflow Configuration

Workflows are defined in JSON format:

```json
{
  "name": "high_risk_decision",
  "description": "High-risk AI decision approval",
  "approval_type": "multi_level",
  "timeout_seconds": 3600,
  "approvers": [
    {
      "level": 1,
      "users": ["manager@company.com"],
      "channels": ["slack", "email"]
    },
    {
      "level": 2,
      "users": ["director@company.com"],
      "channels": ["teams", "pagerduty"],
      "escalate_after": 1800
    }
  ],
  "auto_approve_below_threshold": 0.3,
  "auto_reject_above_threshold": 0.9
}
```

## Development

### Local Development Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run with auto-reload
uvicorn main:app --reload --port 8200

# Run tests
pytest tests/
```

### Docker Development

```bash
# Build and run
docker build -f Dockerfile -t acgs2-hitl-approvals .
docker run -p 8200:8200 acgs2-hitl-approvals
```

## Deployment

### Docker Compose

```yaml
hitl-approvals:
  build:
    context: ./services/hitl_approvals
    dockerfile: Dockerfile
  ports:
    - "8200:8200"
  environment:
    - HITL_APPROVALS_PORT=8200
    - REDIS_URL=redis://redis:6379/0
    - SLACK_BOT_TOKEN=${SLACK_BOT_TOKEN}
  depends_on:
    - redis
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: hitl-approvals
spec:
  replicas: 2
  selector:
    matchLabels:
      app: hitl-approvals
  template:
    metadata:
      labels:
        app: hitl-approvals
    spec:
      containers:
      - name: hitl-approvals
        image: acgs2/hitl-approvals:latest
        ports:
        - containerPort: 8200
        env:
        - name: HITL_APPROVALS_PORT
          value: "8200"
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: redis-secret
              key: url
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8200
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8200
          initialDelaySeconds: 5
          periodSeconds: 5
```

## Approval Workflow

### 1. Request Submission
- AI agent submits decision for human approval
- System evaluates decision risk and context
- Routes to appropriate approval workflow

### 2. Notification Delivery
- Sends notifications via configured channels
- Includes decision context and options
- Provides direct approval/rejection links

### 3. Approval Process
- Approvers review decision details
- Can request additional information
- Make approval/rejection decision

### 4. Decision Execution
- Approved decisions are executed by AI agent
- Rejected decisions trigger fallback actions
- Escalation occurs on timeout

### 5. Audit Logging
- Complete audit trail of approval process
- Decision rationales and timestamps
- Integration with compliance reporting

## Notification Templates

### Slack Message Format
```
🤖 AI Decision Requires Approval

*Decision ID:* `DEC-2024-001`
*Risk Level:* 🔴 High
*Description:* Large financial transaction approval

*Options:*
✅ Approve | ❌ Reject | ❓ Request Info

*Timeout:* 1 hour remaining
```

### Email Template
```html
<h2>AI Decision Approval Required</h2>

<p><strong>Decision ID:</strong> DEC-2024-001</p>
<p><strong>Risk Level:</strong> High</p>
<p><strong>Description:</strong> Large financial transaction approval</p>

<p><strong>Decision Context:</strong></p>
<ul>
<li>Transaction Amount: $1,000,000</li>
<li>Account: Corporate Savings</li>
<li>AI Confidence: 85%</li>
</ul>

<div style="margin: 20px 0;">
  <a href="https://approvals.company.com/approve/DEC-2024-001" style="background: green; color: white; padding: 10px; text-decoration: none;">Approve</a>
  <a href="https://approvals.company.com/reject/DEC-2024-001" style="background: red; color: white; padding: 10px; text-decoration: none;">Reject</a>
</div>
```

## Monitoring

### Metrics

Prometheus metrics exposed at `/metrics`:

- `hitl_approvals_pending_total` - Currently pending approvals
- `hitl_approvals_completed_total` - Total completed approvals
- `hitl_approvals_timeout_total` - Approvals that timed out
- `hitl_notifications_sent_total` - Notifications sent by channel
- `hitl_approval_duration_seconds` - Time to complete approvals

### Logging

Structured logging includes:

- Approval request events
- Notification delivery status
- Approver actions and decisions
- Escalation events
- Error conditions with context

## Security

### Authentication & Authorization
- JWT-based authentication for API access
- Role-based approval permissions
- Audit logging for all approval actions
- Secure notification delivery

### Data Protection
- Encryption of sensitive approval data
- Secure deletion of expired approvals
- Compliance with data retention policies

### Access Control
- Multi-level approval hierarchies
- Emergency bypass procedures
- Audit trail for all access

## Testing

### Unit Tests

```bash
pytest tests/test_approval_engine.py -v
pytest tests/test_notification_delivery.py -v
pytest tests/test_workflow_configuration.py -v
```

### Integration Tests

```bash
pytest tests/integration/test_full_workflow.py -v
pytest tests/integration/test_notification_channels.py -v
```

### Approval Simulation

```bash
# Simulate approval workflow
python tests/simulation/approval_workflow.py --workflow high_risk --approvers 3
```

## Integration Examples

### AI Agent Integration

```python
from acgs2_sdk.services import HITLApprovalsService

# Create approval request
approval = await hitl_client.create_approval({
    "decision_type": "financial_transaction",
    "risk_score": 0.8,
    "context": {
        "amount": 1000000,
        "account": "corporate_savings",
        "ai_confidence": 0.85
    },
    "workflow": "high_risk_financial"
})

# Check approval status
status = await hitl_client.get_approval_status(approval.id)
if status == "approved":
    # Execute the transaction
    await execute_transaction(approval.context)
```

### Webhook Integration

```python
# Webhook endpoint for approval decisions
@app.post("/webhooks/approvals")
async def handle_approval_webhook(request: ApprovalWebhook):
    if request.status == "approved":
        # Process approved decision
        await process_decision(request.approval_id, request.decision_data)
    elif request.status == "rejected":
        # Handle rejection
        await handle_rejection(request.approval_id, request.reason)
```

## Contributing

When adding new notification channels or approval workflows:

1. Create channel-specific implementation
2. Add configuration schema
3. Implement comprehensive tests
4. Update API documentation
5. Add monitoring metrics

## Troubleshooting

### Common Issues

1. **Notifications not delivered**: Check channel configuration and credentials
2. **Approvals timing out**: Review timeout configuration and approver availability
3. **Webhook failures**: Verify endpoint URLs and authentication
4. **High latency**: Check Redis connection and message queue status

### Debug Mode

Enable detailed logging:

```bash
export LOG_LEVEL=DEBUG
export HITL_DEBUG_NOTIFICATIONS=true
uvicorn main:app --reload
```

## License

This service is part of the ACGS-2 platform and follows the same license terms.
