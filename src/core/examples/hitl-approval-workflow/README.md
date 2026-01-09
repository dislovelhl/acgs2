# HITL Approval Workflow Example

This example demonstrates how to implement Human-in-the-Loop (HITL) approval workflows in ACGS-2. HITL workflows ensure that critical AI governance decisions require human oversight and approval before execution.

## What You'll Learn

- How to create approval chains with multiple steps
- Role-based approval routing
- Time-based escalation policies
- Integration with notification systems
- Audit trail and compliance tracking

## Architecture Overview

```
AI Decision → Approval Chain → Human Approval → Execution
     ↓             ↓             ↓            ↓
  Context      Escalation    Notifications  Audit Log
  Analysis     Policies       (Slack/Teams) Compliance
```

## Project Structure

```
hitl-approval-workflow/
├── approval_chain.json     # Sample approval chain configuration
├── demo_workflow.py        # Python script demonstrating workflow
├── test_approvals.py       # Test cases for approval scenarios
├── requirements.txt        # Dependencies
└── README.md              # This file
```

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the demo
python demo_workflow.py
```

## Sample Approval Chain

The example includes a three-step approval chain:

1. **Initial Review** (10 minutes)

   - Approvers: junior_analysts
   - Escalation: senior_analysts (after 10 min)

2. **Compliance Check** (30 minutes)

   - Approvers: compliance_officers
   - Escalation: compliance_managers (after 30 min)

3. **Executive Approval** (60 minutes)
   - Approvers: executives
   - Escalation: ceo (after 60 min)

## Workflow Scenarios

### Scenario 1: Standard Approval Flow

```python
# Create approval request
request_id = await create_approval_request(
    chain_id="critical-ai-decisions",
    title="Deploy High-Risk AI Model",
    description="Deploying GPT-4 based model for customer service",
    requester_id="ml_engineer_1",
    context={
        "risk_level": "high",
        "model_type": "gpt-4",
        "use_case": "customer_service"
    }
)

# Check status
status = await get_approval_status(request_id)
print(f"Status: {status['request']['status']}")
print(f"Current Step: {status['current_step']['name']}")
print(f"Time Remaining: {status['time_remaining_minutes']} minutes")

# Submit approval (as authorized user)
await approve_request(
    request_id=request_id,
    approver_id="compliance_officer_1",
    decision="approved",
    rationale="Model meets all compliance requirements"
)
```

### Scenario 2: Escalation Flow

```python
# Request times out and escalates automatically
# Notifications sent to escalation approvers
# Original approvers can still approve, but escalated users are added

escalation_status = await get_approval_status(request_id)
print(f"Escalations: {len(escalation_status['request']['escalations'])}")
```

### Scenario 3: Rejection Flow

```python
# Request is rejected by an approver
await approve_request(
    request_id=request_id,
    approver_id="executive_1",
    decision="rejected",
    rationale="Risk level too high for current business case"
)

# Workflow terminates with audit trail
final_status = await get_approval_status(request_id)
print(f"Final Status: {final_status['request']['status']}")
```

## Notification Integration

The workflow supports multiple notification channels:

### Slack Notifications

```json
{
  "channel": "slack",
  "webhook_url": "https://hooks.slack.com/services/...",
  "template": {
    "text": "🚨 *Approval Required*: {title}",
    "blocks": [
      {
        "type": "section",
        "text": {
          "type": "mrkdwn",
          "text": "*{title}*\n{description}\n\nApprovers: {approvers}\nTime Remaining: {time_remaining}min"
        }
      },
      {
        "type": "actions",
        "elements": [
          {
            "type": "button",
            "text": { "type": "plain_text", "text": "View Details" },
            "url": "https://acgs2.company.com/approvals/{request_id}"
          }
        ]
      }
    ]
  }
}
```

### Microsoft Teams

```json
{
  "channel": "teams",
  "webhook_url": "https://outlook.office.com/webhook/...",
  "template": {
    "@type": "MessageCard",
    "@context": "http://schema.org/extensions",
    "summary": "Approval Required",
    "title": "🚨 {title}",
    "text": "{description}",
    "potentialAction": [
      {
        "@type": "OpenUri",
        "name": "Review Request",
        "targets": [
          {
            "os": "default",
            "uri": "https://acgs2.company.com/approvals/{request_id}"
          }
        ]
      }
    ]
  }
}
```

## Expected Demo Output

```
ACGS-2 HITL Approval Workflow Demo
===================================

1. Creating approval chain...
   ✅ Chain 'critical-ai-decisions' created

2. Creating approval request...
   ✅ Request 'req-12345' created

3. Checking initial status...
   📋 Status: pending
   👥 Current Step: Initial Review
   ⏰ Time Remaining: 10 minutes
   👤 Approvers: ['alice@company.com', 'bob@company.com']

4. Submitting approval (Step 1)...
   ✅ Approval recorded

5. Checking status after approval...
   📋 Status: pending
   👥 Current Step: Compliance Check
   ⏰ Time Remaining: 30 minutes
   👤 Approvers: ['charlie@company.com']

6. Submitting final approval...
   ✅ Approval recorded

7. Checking final status...
   📋 Status: approved
   ✅ Workflow completed successfully

8. Audit trail...
   📊 Total approvals: 2
   📊 Total escalations: 0
   📊 Total notifications: 4

Demo completed! 🎉
```

## Advanced Features

### Custom Escalation Rules

```json
{
  "escalation_rules": [
    {
      "delay_minutes": 15,
      "escalate_to": ["senior_approver@company.com"],
      "notification_channels": ["slack", "email"],
      "max_escalations": 2
    }
  ]
}
```

### Conditional Approval Chains

```json
{
  "trigger_conditions": {
    "risk_level": "high",
    "model_type": ["gpt-4", "claude-3"],
    "deployment_environment": "production"
  }
}
```

### Audit Trail Integration

```python
# Retrieve complete audit trail
audit_trail = await get_audit_trail(request_id)
for entry in audit_trail:
    print(f"{entry['timestamp']}: {entry['action']} by {entry['actor_id']}")
```

## Integration with ACGS-2 Services

### Agent Bus Integration

```python
# Trigger approval from AI decision
from src.core.shared.agent_bus_client import AgentBusClient

client = AgentBusClient()
decision_result = await client.evaluate_governance(ai_decision_context)

if decision_result.get("requires_approval"):
    approval_request = await create_hitl_approval(
        chain_id="ai-safety-approval",
        context=decision_result
    )
```

### Compliance Documentation

```python
# Generate compliance evidence for approvals
from src.core.services.compliance_docs.client import ComplianceClient

compliance_client = ComplianceClient()
evidence = await compliance_client.generate_evidence({
    "framework": "soc2",
    "approval_request_id": request_id,
    "approvals": approval_history
})
```

## Next Steps

1. **Customize Approval Chains**: Modify the chain configuration for your organization's needs
2. **Integrate Notifications**: Set up Slack/Teams webhooks for your workspace
3. **Add Authentication**: Implement user authentication and authorization
4. **Monitor Performance**: Set up dashboards for approval metrics and SLAs
5. **Advanced Workflows**: Implement parallel approvals, conditional routing, and custom business logic

## Production Deployment

For production deployment:

1. Configure Redis for persistence
2. Set up notification webhooks
3. Configure SSL/TLS certificates
4. Set up monitoring and alerting
5. Implement rate limiting and security controls
6. Configure audit log retention policies

## Troubleshooting

### Common Issues

**Approvals not triggering**: Check trigger conditions and chain activation status
**Notifications failing**: Verify webhook URLs and network connectivity
**Escalations not working**: Check Redis connectivity and timer configuration
**Audit logs missing**: Verify audit callback configuration

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
export HITL_DEBUG=true

# Run with verbose output
python demo_workflow.py --verbose
```

## Related Examples

- [Basic Governance](../basic-governance/) - Simple approval workflows
- [Content Moderation](../content-moderation/) - Content-specific approvals
- [Code Review Assistant](../code-review-assistant/) - Development workflow approvals
