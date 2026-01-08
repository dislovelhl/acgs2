# 🚀 ACGS-2 Quickstart Guide

Get started with ACGS-2 (Advanced Constitutional Governance System) in under 30 minutes. This guide will walk you through setting up your development environment and running your first governance policy.

## 📋 Prerequisites

Before you begin, ensure you have:

- **Docker & Docker Compose** (v20.10+)
- **Python 3.11+** (optional, for local development)
- **Git** (for cloning repositories)
- **4GB+ RAM** (for running all services)

## 🏃‍♂️ Quick Start (5 minutes)

### Option 1: One-Command Setup (Recommended)

```bash
# Clone the repository
git clone https://github.com/dislovelhl/acgs2/ACGS-PGP2.git
cd ACGS-PGP2

# Start the complete development environment
docker-compose up -d

# Wait for services to be ready (about 2 minutes)
docker-compose logs -f | grep -E "(healthy|ready|started)"

# Open your browser to the API Gateway
open http://localhost:8080
```

That's it! ACGS-2 is now running with all services operational.

### Option 2: Local Development Setup

```bash
# Clone and setup
git clone https://github.com/dislovelhl/acgs2/ACGS-PGP2.git
cd ACGS-PGP2

# Install dependencies
pip install -r src/core/config/requirements_optimized.txt

# Start infrastructure services
docker-compose up -d redis kafka opa

# Run the API Gateway locally
cd src/core/services/api_gateway
uvicorn main:app --reload --host 0.0.0.0 --port 8080
```

## 🎯 Your First Governance Policy (10 minutes)

Let's create and test a simple governance policy that ensures AI responses are helpful and truthful.

### Step 1: Create a Policy

```bash
# Create a new policy file
cat > my_first_policy.rego << 'EOF'
package acgs2.policies.helpful_truthful

# Policy for ensuring AI responses are helpful and truthful
default allow = false

allow {
    input.intent.classification == "helpful"
    input.intent.confidence > 0.8
    not contains_prohibited_content(input.response)
}

contains_prohibited_content(response) {
    prohibited_words := ["harmful", "dangerous", "illegal"]
    some word in prohibited_words
    contains(lower(response), lower(word))
}

# Provide helpful feedback
violations[reason] {
    not allow
    reason := "Response must be helpful and truthful"
}
EOF
```

### Step 2: Deploy the Policy

```bash
# Copy to OPA policies directory
cp my_first_policy.rego policies/rego/

# The policy is automatically loaded by OPA
# No restart required!
```

### Step 3: Test Your Policy

```bash
# Test with a compliant request
curl -X POST http://localhost:8080/api/v1/governance/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "intent": {"classification": "helpful", "confidence": 0.95},
    "response": "I can help you with that Python question!"
  }'

# Expected: {"allow": true, "violations": []}

# Test with a non-compliant request
curl -X POST http://localhost:8080/api/v1/governance/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "intent": {"classification": "harmful", "confidence": 0.9},
    "response": "This could be dangerous advice"
  }'

# Expected: {"allow": false, "violations": ["Response must be helpful and truthful"]}
```

### Step 4: Try HITL Approvals (Advanced)

ACGS-2 includes Human-in-the-Loop workflows for critical decisions:

```bash
# Create an approval request
curl -X POST http://localhost:8200/api/v1/approvals/ \
  -H "Content-Type: application/json" \
  -d '{
    "chain_id": "sample-chain",
    "title": "Critical AI Decision",
    "description": "Deploy high-risk model to production",
    "requester_id": "developer",
    "priority": "high",
    "context": {"risk_level": "high", "model": "gpt-4"}
  }'

# Check approval status
curl http://localhost:8200/api/v1/approvals/{request_id}/status

# Approve the request (as authorized user)
curl -X POST http://localhost:8200/api/v1/approvals/{request_id}/approve \
  -H "Content-Type: application/json" \
  -d '{
    "approver_id": "approver",
    "decision": "approved",
    "rationale": "Risks are acceptable"
  }'
```

## 🏗️ Architecture Overview

ACGS-2 consists of multiple specialized services:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   API Gateway   │    │   Agent Bus     │    │   Policy        │
│   (Port 8080)   │◄──►│   (Port 8000)   │◄──►│   Registry      │
│                 │    │                 │    │   (Port 8181)   │
│ • Load Balancing│    │ • Intent        │    │ • OPA Engine    │
│ • CORS Handling │    │   Classification│    │ • Policy        │
│ • Request       │    │ • PACAR         │    │   Evaluation    │
│   Routing       │    │   Verification  │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Compliance Docs │    │  HITL Approvals │    │   Audit Service │
│   (Port 8100)   │    │   (Port 8200)   │    │   (Port 8300)   │
│                 │    │                 │    │                 │
│ • SOC 2/ISO 27001│    │ • Approval      │    │ • Blockchain    │
│ • GDPR/EU AI Act│    │   Chains        │    │ • Audit Ledger  │
│ • Evidence Export│    │ • Escalation    │    │ • ZKP Proofs   │
│                 │    │ • Notifications  │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🔧 Development Workflow

### 1. Local Development

```bash
# Start all services
docker-compose up -d

# View service logs
docker-compose logs -f api_gateway

# Run tests
docker-compose exec api_gateway pytest

# Stop services
docker-compose down
```

### 2. Making Changes

```bash
# Edit code in your IDE
code services/api_gateway/main.py

# Services auto-reload on changes
# Test your changes immediately
curl http://localhost:8080/health
```

### 3. Adding New Policies

```bash
# Create policy in policies/rego/
vi policies/rego/my_policy.rego

# Test policy syntax
docker-compose exec opa opa check policies/rego/my_policy.rego

# Test policy evaluation
curl -X POST http://localhost:8000/api/v1/policies/evaluate \
  -d '{"input": {"test": "data"}}'
```

## 📚 Example Projects

### Basic Intent Classification

```python
from acgs2_sdk import GovernanceClient

client = GovernanceClient(base_url="http://localhost:8080")

# Classify intent
result = client.classify_intent("How do I write a Python function?")
print(f"Intent: {result['classification']} (confidence: {result['confidence']})")

# Evaluate governance
evaluation = client.evaluate_governance({
    "intent": result,
    "response": "Here's how to write a Python function..."
})
print(f"Allowed: {evaluation['allow']}")
```

### Advanced Multi-turn Conversation

```python
# Track conversation context
conversation = client.create_conversation()

# First message
msg1 = conversation.evaluate({
    "message": "Tell me about machine learning",
    "context": []
})

# Follow-up with context
msg2 = conversation.evaluate({
    "message": "How does it work?",
    "context": [msg1["response"]]
})

print(f"Conversation safe: {conversation.is_safe()}")
```

## 🧪 Testing Your Setup

Run the comprehensive test suite:

```bash
# Run all tests
docker-compose exec api_gateway pytest --cov=. --cov-report=html

# Run specific service tests
docker-compose exec agent_bus pytest tests/test_intent_classifier.py

# View coverage report
open htmlcov/index.html
```

## 🎥 Video Tutorials

- [Getting Started (5 min)](https://acgs2.dev/videos/getting-started)
- [Writing Your First Policy (10 min)](https://acgs2.dev/videos/first-policy)
- [Intent Classification Deep Dive (15 min)](https://acgs2.dev/videos/intent-classification)
- [Multi-turn Conversation Governance (12 min)](https://acgs2.dev/videos/multi-turn)

## 📞 Need Help?

- **Documentation**: https://docs.acgs2.dev
- **Community**: https://community.acgs2.dev
- **Issues**: https://github.com/dislovemartin/ACGS-PGP2/issues
- **Slack**: https://acgs2.dev/slack

## ✅ Success Checklist

- [ ] ACGS-2 services are running (`docker-compose ps`)
- [ ] API Gateway responds (`curl http://localhost:8080/health`)
- [ ] Created and deployed a policy
- [ ] Tested policy evaluation
- [ ] Ran test suite successfully
- [ ] Understand the three-service architecture

**Congratulations!** You're now ready to build governance policies with ACGS-2. 🎉
