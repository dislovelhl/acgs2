# ACGS-2 Quickstart Guide

<!-- Constitutional Hash: cdd01ef066bc6cf2 -->

> **Goal**: Get from zero to your first policy evaluation in under 30 minutes
> **Version**: 1.0.0
> **Last Updated**: 2025-01-02
> **Target Audience**: Developers new to ACGS-2 and AI governance

[![Time to Complete](https://img.shields.io/badge/Time-30%20min-green?style=flat-square)]()
[![Difficulty](https://img.shields.io/badge/Difficulty-Beginner-blue?style=flat-square)]()
[![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20macOS%20%7C%20Windows-orange?style=flat-square)]()

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Quick Setup (5 Minutes)](#quick-setup-5-minutes)
4. [Understanding ACGS-2 Architecture](#understanding-acgs-2-architecture)
5. [Your First Policy Evaluation (10 Minutes)](#your-first-policy-evaluation-10-minutes)
6. [Understanding Rego Policies](#understanding-rego-policies)
7. [Working with the Agent Bus](#working-with-the-agent-bus)
8. [Constitutional Governance Basics](#constitutional-governance-basics)
9. [Interactive Experimentation](#interactive-experimentation)
10. [Video Tutorials](#video-tutorials)
11. [Next Steps](#next-steps)
12. [Troubleshooting](#troubleshooting)
13. [Feedback](#feedback)

---

## Overview

Welcome to ACGS-2 (Advanced Constitutional Governance System)! This quickstart guide will help you understand and start using our AI governance platform in under 30 minutes.

### What is ACGS-2?

ACGS-2 is an enterprise-grade AI governance platform that provides:

- **Constitutional Compliance**: Ensures AI systems operate within defined ethical and operational boundaries
- **Real-time Policy Evaluation**: Sub-millisecond decision making for AI governance
- **Adaptive Governance**: ML-powered dynamic threshold adjustment
- **Enterprise Security**: Zero-trust architecture with military-grade protection

### What You'll Learn

By the end of this guide, you'll be able to:

1. Start the ACGS-2 development environment with a single command
2. Evaluate your first governance policy using OPA (Open Policy Agent)
3. Understand the basic architecture and components
4. Write and test simple governance policies
5. Query the Agent Bus for AI governance decisions

### Time Estimate

| Section | Time | What You'll Do |
|---------|------|----------------|
| Quick Setup | 5 min | Install prerequisites and start services |
| First Policy | 10 min | Evaluate a simple policy |
| Understanding Architecture | 5 min | Learn the key components |
| Experimentation | 10 min | Modify policies and test |
| **Total** | **30 min** | Complete working environment |

---

## Prerequisites

Before you begin, ensure you have the following installed on your system.

### Required Software

| Software | Minimum Version | Installation Link | Verification Command |
|----------|-----------------|-------------------|---------------------|
| **Docker** | 24.0+ | [docker.com/get-docker](https://docs.docker.com/get-docker/) | `docker --version` |
| **Docker Compose** | 2.20+ | Included with Docker Desktop | `docker compose version` |
| **Git** | 2.0+ | [git-scm.com](https://git-scm.com/) | `git --version` |
| **Python** | 3.11+ | [python.org](https://www.python.org/) | `python --version` |
| **curl** | Any | Pre-installed on most systems | `curl --version` |

### System Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| **RAM** | 4 GB | 8 GB |
| **Disk Space** | 5 GB | 10 GB |
| **CPU Cores** | 2 | 4+ |
| **Network** | Internet (for initial setup) | Internet |

### Verify Prerequisites

Run this script to check all prerequisites:

```bash
#!/bin/bash
# Save as check_prerequisites.sh and run with: bash check_prerequisites.sh

echo "=== ACGS-2 Prerequisite Check ==="
echo ""

# Check Docker
if command -v docker &> /dev/null; then
    docker_version=$(docker --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
    echo "✅ Docker: $docker_version"
else
    echo "❌ Docker: Not installed"
fi

# Check Docker Compose
if docker compose version &> /dev/null; then
    compose_version=$(docker compose version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
    echo "✅ Docker Compose: $compose_version"
else
    echo "❌ Docker Compose: Not installed"
fi

# Check Git
if command -v git &> /dev/null; then
    git_version=$(git --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
    echo "✅ Git: $git_version"
else
    echo "❌ Git: Not installed"
fi

# Check Python
if command -v python3 &> /dev/null; then
    python_version=$(python3 --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
    echo "✅ Python: $python_version"
else
    echo "❌ Python: Not installed"
fi

# Check if Docker is running
if docker info &> /dev/null; then
    echo "✅ Docker daemon: Running"
else
    echo "❌ Docker daemon: Not running (start Docker Desktop or docker service)"
fi

echo ""
echo "=== Check Complete ==="
```

> **Note for Windows Users**: Use PowerShell or WSL2 (Windows Subsystem for Linux) for the best experience. Docker Desktop for Windows includes Docker Compose.

---

## Quick Setup (5 Minutes)

Let's get ACGS-2 running on your machine!

### Step 1: Clone the Repository

```bash
# Clone the ACGS-2 repository
git clone https://github.com/dislovelhl/acgs2.git

# Navigate to the project directory
cd ACGS-2
```

### Step 2: Copy Environment Configuration

ACGS-2 uses a centralized configuration system. We provide a development-ready `.env.dev` file:

```bash
# Copy the development environment file
cp .env.dev .env
```

> **What's in .env.dev?** It contains pre-configured settings for local development including:
> - Service URLs (OPA, Redis, Kafka)
> - Constitutional hash for governance validation
> - Development-safe security settings

### Step 3: Start All Services

With Docker Compose, you can start the entire stack with one command:

```bash
# Start all ACGS-2 services in detached mode
docker compose -f docker-compose.dev.yml --env-file .env.dev up -d
```

Expected output:
```
[+] Running 5/5
 ✔ Network acgs2_acgs-dev       Created
 ✔ Container acgs2-zookeeper-1  Started
 ✔ Container acgs2-redis-1      Started
 ✔ Container acgs2-opa-1        Started
 ✔ Container acgs2-kafka-1      Started
 ✔ Container acgs2-agent-bus-1  Started
 ✔ Container acgs2-api-gateway-1 Started
```

### Step 4: Verify Services Are Running

```bash
# Check that all containers are running
docker compose -f docker-compose.dev.yml ps

# Expected output (all should show "running"):
# NAME                    SERVICE        STATUS         PORTS
# acgs2-agent-bus-1       agent-bus      running        0.0.0.0:8000->8000/tcp
# acgs2-api-gateway-1     api-gateway    running        0.0.0.0:8080->8080/tcp
# acgs2-kafka-1           kafka          running        0.0.0.0:19092->19092/tcp
# acgs2-opa-1             opa            running        0.0.0.0:8181->8181/tcp
# acgs2-redis-1           redis          running        0.0.0.0:6379->6379/tcp
# acgs2-zookeeper-1       zookeeper      running        0.0.0.0:2181->2181/tcp
```

### Step 5: Test OPA Health

Verify that the Open Policy Agent (OPA) is responding:

```bash
# Check OPA health endpoint
curl -s http://localhost:8181/health

# Expected output:
# {}  (empty JSON indicates healthy)

# Alternative: check with jq formatting
curl -s http://localhost:8181/health | python3 -m json.tool
```

### Service URLs

After successful startup, these services are available:

| Service | URL | Description |
|---------|-----|-------------|
| **OPA (Policy Engine)** | http://localhost:8181 | Policy evaluation and management |
| **Agent Bus** | http://localhost:8000 | Core governance service |
| **API Gateway** | http://localhost:8080 | Unified entry point |
| **Redis** | localhost:6379 | Caching and state |
| **Kafka** | localhost:19092 | Event streaming |

**Congratulations!** You now have ACGS-2 running locally. Let's evaluate your first policy!

---

## Understanding ACGS-2 Architecture

Before diving into policy evaluation, let's understand how ACGS-2 works.

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            ACGS-2 Architecture                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│    ┌──────────────┐         ┌──────────────┐         ┌──────────────┐       │
│    │   Client     │         │  API Gateway │         │  Agent Bus   │       │
│    │  Application │ ──────► │   (8080)     │ ──────► │   (8000)     │       │
│    └──────────────┘         └──────────────┘         └──────┬───────┘       │
│                                                              │               │
│                                                              ▼               │
│    ┌──────────────────────────────────────────────────────────────────┐     │
│    │                     Constitutional Validation                     │     │
│    │                 Hash: cdd01ef066bc6cf2                           │     │
│    └──────────────────────────────────────────────────────────────────┘     │
│                                      │                                       │
│                                      ▼                                       │
│    ┌──────────────┐         ┌──────────────┐         ┌──────────────┐       │
│    │    OPA       │◄────────│   Impact     │         │ Deliberation │       │
│    │  (8181)      │         │   Scorer     │────────►│    Layer     │       │
│    └──────────────┘         └──────────────┘         └──────────────┘       │
│                                                              │               │
│    ┌──────────────┐         ┌──────────────┐                │               │
│    │   Redis      │◄────────│   Kafka      │◄───────────────┘               │
│    │   (6379)     │         │   (19092)    │                                │
│    └──────────────┘         └──────────────┘                                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Core Components

#### 1. Open Policy Agent (OPA)

OPA is the policy decision point. It evaluates governance policies written in Rego, a declarative language.

```
┌─────────────────────────────────────────────────────┐
│                    OPA (Port 8181)                   │
├─────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────┐    │
│  │             Policy Storage                   │    │
│  │  ├── constitutional.rego                    │    │
│  │  ├── rbac.rego                              │    │
│  │  ├── compliance.rego                        │    │
│  │  └── ratelimit.rego                         │    │
│  └─────────────────────────────────────────────┘    │
│                        │                             │
│                        ▼                             │
│  ┌─────────────────────────────────────────────┐    │
│  │           Policy Evaluation Engine           │    │
│  │                                              │    │
│  │    Input (JSON) ──► Rego Rules ──► Decision │    │
│  └─────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────┘
```

**Key Features:**
- Sub-millisecond policy evaluation (P99: 0.328ms)
- Declarative policy language (Rego)
- Hot-reloading of policies
- REST API for queries

#### 2. Agent Bus

The Agent Bus is the central orchestration service that:
- Routes messages between agents
- Enforces constitutional compliance
- Calculates impact scores
- Coordinates deliberation for high-risk decisions

#### 3. Constitutional Validation

Every request goes through constitutional validation to ensure:
- The constitutional hash matches (`cdd01ef066bc6cf2`)
- No deprecated features are used
- Tenant isolation is maintained

### Message Flow

```
┌────────────────────────────────────────────────────────────────────────────┐
│                          Message Flow Diagram                               │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. Request Received                                                        │
│     ┌──────────┐                                                           │
│     │  Agent   │────────────────────────────────────────────┐              │
│     └──────────┘                                            │              │
│                                                             ▼              │
│  2. Constitutional Validation                                              │
│     ┌────────────────────────────────────────────────────────────────┐    │
│     │  Validate hash: cdd01ef066bc6cf2                               │    │
│     │  Check: no deprecated features (eval, legacy_sync)             │    │
│     │  Verify: tenant_id present                                     │    │
│     └────────────────────────────────────────────────────────────────┘    │
│                               │                                             │
│                   ┌───────────┴───────────┐                                │
│                   ▼                       ▼                                 │
│  3a. Low Risk (score < 0.8)      3b. High Risk (score >= 0.8)             │
│     ┌──────────────┐                 ┌──────────────┐                      │
│     │  Fast Lane   │                 │ Deliberation │                      │
│     │  (Direct)    │                 │    Layer     │                      │
│     └──────────────┘                 └──────────────┘                      │
│            │                                │                               │
│            ▼                                ▼                               │
│  4. Audit & Delivery                                                        │
│     ┌────────────────────────────────────────────────────────────────┐    │
│     │  Log to blockchain audit ledger                                │    │
│     │  Deliver to target agent                                       │    │
│     │  Emit metrics to Prometheus                                    │    │
│     └────────────────────────────────────────────────────────────────┘    │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## Your First Policy Evaluation (10 Minutes)

Now let's evaluate your first governance policy!

### Understanding Policy Structure

A policy query in OPA consists of:
1. **Policy Path**: Where the policy is defined (e.g., `acgs/constitutional/allow`)
2. **Input Data**: JSON data to evaluate (e.g., `{"constitutional_hash": "cdd01ef066bc6cf2"}`)
3. **Decision**: The policy's response (e.g., `true` or `false`)

### Step 1: View Available Policies

First, let's see what policies are loaded in OPA:

```bash
# List all loaded policies
curl -s http://localhost:8181/v1/policies | python3 -m json.tool

# You should see policies like:
# - acgs/constitutional
# - acgs/rbac
# - acgs/compliance
# - acgs/ratelimit
```

### Step 2: Evaluate the Constitutional Policy

The constitutional policy is the foundation of ACGS-2 governance. Let's evaluate it:

```bash
# Query the constitutional allow rule
curl -s -X POST http://localhost:8181/v1/data/acgs/constitutional/allow \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "constitutional_hash": "cdd01ef066bc6cf2",
      "tenant_id": "my-tenant",
      "features": []
    }
  }' | python3 -m json.tool
```

**Expected Output:**
```json
{
    "result": true
}
```

**What happened?**
- We sent a request with the correct constitutional hash
- The policy checked our input against the rules
- Since all conditions were met, it returned `true`

### Step 3: Test a Policy Violation

Now let's see what happens when we violate the policy:

```bash
# Try with wrong constitutional hash
curl -s -X POST http://localhost:8181/v1/data/acgs/constitutional/allow \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "constitutional_hash": "wrong_hash",
      "tenant_id": "my-tenant",
      "features": []
    }
  }' | python3 -m json.tool
```

**Expected Output:**
```json
{
    "result": false
}
```

**What happened?**
- The constitutional hash didn't match
- The policy denied the request

### Step 4: Check for Violations

Let's get more details about why a request was denied:

```bash
# Query the violation message
curl -s -X POST http://localhost:8181/v1/data/acgs/constitutional/violation \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "constitutional_hash": "wrong_hash",
      "tenant_id": "my-tenant",
      "features": []
    }
  }' | python3 -m json.tool
```

**Expected Output:**
```json
{
    "result": [
        "Constitutional hash mismatch or deprecated features detected"
    ]
}
```

### Step 5: Test Deprecated Features

The policy also checks for deprecated features:

```bash
# Try using deprecated 'eval' feature
curl -s -X POST http://localhost:8181/v1/data/acgs/constitutional/allow \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "constitutional_hash": "cdd01ef066bc6cf2",
      "tenant_id": "my-tenant",
      "features": ["eval"]
    }
  }' | python3 -m json.tool
```

**Expected Output:**
```json
{
    "result": false
}
```

The `eval` feature is blocked because it's a security risk (OWASP A03:2021 Injection).

### Python Client Example

You can also query OPA programmatically with Python:

```python
#!/usr/bin/env python3
"""Simple OPA policy evaluation client."""

import requests
import json

OPA_URL = "http://localhost:8181"

def evaluate_policy(policy_path: str, input_data: dict) -> dict:
    """
    Query an OPA policy with input data.

    Args:
        policy_path: Path to the policy rule (e.g., "acgs/constitutional/allow")
        input_data: Dictionary of input data for the policy

    Returns:
        Policy evaluation result
    """
    try:
        response = requests.post(
            f"{OPA_URL}/v1/data/{policy_path}",
            json={"input": input_data},
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

def main():
    print("=== ACGS-2 Policy Evaluation Demo ===\n")

    # Test 1: Valid request
    print("Test 1: Valid constitutional request")
    result = evaluate_policy("acgs/constitutional/allow", {
        "constitutional_hash": "cdd01ef066bc6cf2",
        "tenant_id": "demo-tenant",
        "features": []
    })
    print(f"  Result: {json.dumps(result, indent=2)}")
    print(f"  Decision: {'ALLOW' if result.get('result') else 'DENY'}\n")

    # Test 2: Invalid hash
    print("Test 2: Invalid constitutional hash")
    result = evaluate_policy("acgs/constitutional/allow", {
        "constitutional_hash": "invalid_hash",
        "tenant_id": "demo-tenant",
        "features": []
    })
    print(f"  Result: {json.dumps(result, indent=2)}")
    print(f"  Decision: {'ALLOW' if result.get('result') else 'DENY'}\n")

    # Test 3: Deprecated feature
    print("Test 3: Deprecated feature 'eval'")
    result = evaluate_policy("acgs/constitutional/allow", {
        "constitutional_hash": "cdd01ef066bc6cf2",
        "tenant_id": "demo-tenant",
        "features": ["eval"]
    })
    print(f"  Result: {json.dumps(result, indent=2)}")
    print(f"  Decision: {'ALLOW' if result.get('result') else 'DENY'}\n")

    # Test 4: Get violation details
    print("Test 4: Get violation details")
    result = evaluate_policy("acgs/constitutional/violation", {
        "constitutional_hash": "invalid_hash",
        "tenant_id": "demo-tenant",
        "features": []
    })
    print(f"  Violations: {json.dumps(result, indent=2)}")

if __name__ == "__main__":
    main()
```

Save this as `test_policy.py` and run it:

```bash
# Install requests if needed
pip install requests

# Run the script
python3 test_policy.py
```

---

## Understanding Rego Policies

Rego is the policy language used by OPA. Let's understand how to read and write Rego policies.

### Basic Rego Syntax

```rego
# Package declaration - defines the namespace
package acgs.example

# Default value if no rules match
default allow := false

# A simple rule that allows access
allow {
    input.user == "admin"
    input.action == "read"
}

# You can have multiple rules - they OR together
allow {
    input.user_role == "superuser"
}

# Helper rule for validation
valid_user {
    input.user != null
    count(input.user) > 0
}

# Generate messages for violations
violation[msg] {
    not allow
    msg := sprintf("Access denied for user: %v", [input.user])
}
```

### Key Rego Concepts

| Concept | Description | Example |
|---------|-------------|---------|
| **Package** | Namespace for policies | `package acgs.governance` |
| **Default** | Value when no rules match | `default allow := false` |
| **Rule** | A logical statement | `allow { input.valid }` |
| **Input** | Data provided to the policy | `input.user_id` |
| **Array Access** | Iterate over arrays | `input.roles[_] == "admin"` |
| **Negation** | Check something is NOT true | `not deprecated` |
| **Comprehensions** | Filter/transform data | `[x \| x := input.items[_]; x > 10]` |

### The Constitutional Policy Explained

Let's break down the actual constitutional policy used in ACGS-2:

```rego
# Package declaration - places this policy at acgs.constitutional
package acgs.constitutional

# Default deny - secure by default (fail-closed)
default allow := false

# Main allow rule - all conditions must be true
allow {
    # Condition 1: Constitutional hash must match exactly
    input.constitutional_hash == "cdd01ef066bc6cf2"

    # Condition 2: No deprecated features used
    not deprecated_features_used

    # Condition 3: Tenant ID must be present (multi-tenant enforcement)
    input.tenant_id != null
}

# Helper rule: Check for deprecated features
deprecated_features_used {
    # Block 'eval' - security risk (OWASP A03:2021)
    input.features[_] == "eval"
}

deprecated_features_used {
    # Block legacy synchronous operations
    input.features[_] == "legacy_sync"
}

# Generate violation messages
violation[msg] {
    not allow
    msg := "Constitutional hash mismatch or deprecated features detected"
}
```

### Writing Your First Policy

Let's create a simple AI model governance policy:

```rego
# File: ai_model_governance.rego
package acgs.ai.model

# Default deny - no model deployment without approval
default allow_deployment := false

# Allow deployment if risk score is acceptable
allow_deployment {
    input.model.risk_score < 0.7
    input.model.tested == true
    valid_model_type
}

# High-risk models require human approval
allow_deployment {
    input.model.risk_score >= 0.7
    input.approval.human_approved == true
    input.approval.approver_role == "ai_safety_officer"
}

# Valid model types
valid_model_type {
    allowed_types := ["classifier", "regressor", "generator", "embedder"]
    input.model.type == allowed_types[_]
}

# Generate deployment decision with reason
deployment_decision := {
    "allowed": allow_deployment,
    "reason": reason,
    "model_id": input.model.id
} {
    allow_deployment
    reason := "Model meets deployment criteria"
}

deployment_decision := {
    "allowed": allow_deployment,
    "reason": reason,
    "model_id": input.model.id
} {
    not allow_deployment
    reason := "Model deployment blocked - check risk score and approval status"
}
```

### Testing Your Policy Locally

You can test policies without restarting services:

```bash
# Create a test policy file
cat > /tmp/test_policy.rego << 'EOF'
package test.example

default greeting := "Hello, World!"

greeting := msg {
    input.name != null
    msg := sprintf("Hello, %s!", [input.name])
}
EOF

# Load and test with OPA CLI (if installed)
# Or use Docker:
docker run --rm -v /tmp:/policies openpolicyagent/opa:latest \
    eval -i '{"name": "Developer"}' -d /policies/test_policy.rego \
    'data.test.example.greeting'
```

---

## Working with the Agent Bus

The Agent Bus is the central orchestration service for ACGS-2. Let's explore its API.

### Agent Bus Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            Agent Bus (Port 8000)                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                         API Endpoints                                  │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │  │
│  │  │ /health     │  │ /send       │  │ /deliberate │  │ /metrics    │   │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘   │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                     │                                        │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                    Message Processing Pipeline                         │  │
│  │                                                                        │  │
│  │  ┌──────────┐    ┌──────────────┐    ┌─────────────┐    ┌──────────┐  │  │
│  │  │ Receive  │───►│ Validate     │───►│ Score       │───►│ Route    │  │  │
│  │  │ Message  │    │ Constitution │    │ Impact      │    │ Message  │  │  │
│  │  └──────────┘    └──────────────┘    └─────────────┘    └──────────┘  │  │
│  │                                                                        │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                     │                                        │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                    Integration Points                                  │  │
│  │  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐               │  │
│  │  │ OPA     │   │ Redis   │   │ Kafka   │   │ Prometheus│              │  │
│  │  │ (8181)  │   │ (6379)  │   │ (19092) │   │ (metrics) │              │  │
│  │  └─────────┘   └─────────┘   └─────────┘   └─────────────┘            │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Check Agent Bus Health

```bash
# Check Agent Bus health
curl -s http://localhost:8000/health | python3 -m json.tool

# Expected output includes:
# - service: "agent-bus"
# - status: "healthy"
# - components: (opa, redis, kafka status)
```

### Explore API Documentation

The Agent Bus provides OpenAPI documentation:

```bash
# Get OpenAPI spec (if available)
curl -s http://localhost:8000/openapi.json | python3 -m json.tool

# Or access the Swagger UI in a browser:
# http://localhost:8000/docs (if enabled)
```

### Send a Test Message

Here's how to send a message through the Agent Bus:

```python
#!/usr/bin/env python3
"""Agent Bus message sending example."""

import requests
import json

AGENT_BUS_URL = "http://localhost:8000"

def send_message(payload: dict) -> dict:
    """Send a message through the Agent Bus."""
    try:
        response = requests.post(
            f"{AGENT_BUS_URL}/api/v1/messages",
            json=payload,
            headers={
                "Content-Type": "application/json",
                "X-Constitutional-Hash": "cdd01ef066bc6cf2"
            },
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

def main():
    # Create a test message
    message = {
        "source_agent": "demo-agent",
        "target_agent": "governance-agent",
        "message_type": "policy_check",
        "payload": {
            "action": "deploy_model",
            "model_id": "llm-v1",
            "risk_score": 0.5
        },
        "metadata": {
            "tenant_id": "demo-tenant",
            "timestamp": "2025-01-02T12:00:00Z"
        }
    }

    print("Sending message to Agent Bus...")
    print(f"Payload: {json.dumps(message, indent=2)}")

    result = send_message(message)
    print(f"\nResult: {json.dumps(result, indent=2)}")

if __name__ == "__main__":
    main()
```

---

## Constitutional Governance Basics

Constitutional governance is the core concept in ACGS-2. Let's understand it deeply.

### What is Constitutional AI Governance?

Constitutional governance ensures AI systems:

1. **Operate Within Boundaries**: Defined by constitutional rules
2. **Maintain Integrity**: Verified by cryptographic hashes
3. **Provide Accountability**: Through audit trails
4. **Enable Oversight**: Via human-in-the-loop processes

### The Constitutional Hash

The constitutional hash (`cdd01ef066bc6cf2`) is a cryptographic fingerprint that ensures:

| Property | Description |
|----------|-------------|
| **Immutability** | Rules cannot be silently changed |
| **Verification** | Every request validates against the hash |
| **Auditability** | Changes are tracked and versioned |
| **Consistency** | All services use the same governance rules |

### MACI: Multi-Agent Constitutional Intelligence

MACI is the enforcement framework for constitutional compliance:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            MACI Framework                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                      Role Separation                                    │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                 │ │
│  │  │   Proposer   │  │   Verifier   │  │   Executor   │                 │ │
│  │  │  (Agents)    │  │  (OPA)       │  │  (Agent Bus) │                 │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘                 │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                     │                                        │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                      Strict Mode Enforcement                           │ │
│  │                                                                        │ │
│  │  When MACI_STRICT_MODE=true:                                           │ │
│  │  • All requests must pass constitutional validation                    │ │
│  │  • No bypass mechanisms for production                                 │ │
│  │  • Failed requests are rejected with detailed errors                   │ │
│  │  • Audit logs capture all validation attempts                          │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Impact Scoring

High-risk decisions trigger additional scrutiny:

| Score Range | Risk Level | Processing |
|-------------|------------|------------|
| 0.0 - 0.3 | Low | Fast lane (direct processing) |
| 0.3 - 0.7 | Medium | Standard validation |
| 0.7 - 0.8 | High | Enhanced review |
| 0.8 - 1.0 | Critical | Deliberation layer (HITL) |

### Deliberation Layer

For critical decisions, the deliberation layer provides:

- **Human-in-the-Loop (HITL)**: Human oversight for high-risk actions
- **Consensus Voting**: Multiple agents agree on the decision
- **Time-bounded Decisions**: Automatic escalation if no response
- **Audit Trail**: Complete record of deliberation process

---

## Interactive Experimentation

Now let's experiment with different scenarios!

### Experiment 1: RBAC Policy

Test role-based access control:

```bash
# Check if admin role allows read access
curl -s -X POST http://localhost:8181/v1/data/acgs/rbac/allow_action \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "user": "alice",
      "role": "admin",
      "action": "read",
      "resource": "/api/models"
    }
  }' | python3 -m json.tool

# Try an unauthorized action
curl -s -X POST http://localhost:8181/v1/data/acgs/rbac/allow_action \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "user": "bob",
      "role": "viewer",
      "action": "delete",
      "resource": "/api/models"
    }
  }' | python3 -m json.tool
```

### Experiment 2: Rate Limiting

Test the rate limiting policy:

```bash
# Check rate limit status
curl -s -X POST http://localhost:8181/v1/data/acgs/ratelimit/within_limits \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "client_id": "client-123",
      "request_count": 50,
      "window_seconds": 60,
      "limit": 100
    }
  }' | python3 -m json.tool

# Simulate exceeding limit
curl -s -X POST http://localhost:8181/v1/data/acgs/ratelimit/within_limits \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "client_id": "client-123",
      "request_count": 150,
      "window_seconds": 60,
      "limit": 100
    }
  }' | python3 -m json.tool
```

### Experiment 3: Compliance Checks

Test compliance validation:

```bash
# Check data residency compliance
curl -s -X POST http://localhost:8181/v1/data/acgs/compliance/data_residency_ok \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "data_location": "us-east-1",
      "allowed_regions": ["us-east-1", "us-west-2", "eu-west-1"],
      "data_type": "pii"
    }
  }' | python3 -m json.tool

# Test with non-compliant region
curl -s -X POST http://localhost:8181/v1/data/acgs/compliance/data_residency_ok \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "data_location": "asia-pacific-1",
      "allowed_regions": ["us-east-1", "us-west-2", "eu-west-1"],
      "data_type": "pii"
    }
  }' | python3 -m json.tool
```

### Experiment 4: Time-Based Access

Test time-based access controls:

```bash
# Check if access is allowed during business hours
curl -s -X POST http://localhost:8181/v1/data/acgs/timebased/within_maintenance_window \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "current_hour": 14,
      "current_day": "tuesday",
      "maintenance_start_hour": 2,
      "maintenance_end_hour": 4
    }
  }' | python3 -m json.tool
```

### Interactive Testing Script

Here's a comprehensive testing script:

```python
#!/usr/bin/env python3
"""Interactive ACGS-2 policy testing script."""

import requests
import json
import sys

OPA_URL = "http://localhost:8181"

def query(path: str, input_data: dict) -> dict:
    """Query OPA policy."""
    try:
        resp = requests.post(
            f"{OPA_URL}/v1/data/{path}",
            json={"input": input_data},
            timeout=5
        )
        return resp.json()
    except Exception as e:
        return {"error": str(e)}

def test_constitutional():
    """Test constitutional policy."""
    print("\n=== Constitutional Policy Tests ===")

    tests = [
        ("Valid hash", {"constitutional_hash": "cdd01ef066bc6cf2", "tenant_id": "t1", "features": []}),
        ("Invalid hash", {"constitutional_hash": "wrong", "tenant_id": "t1", "features": []}),
        ("No tenant", {"constitutional_hash": "cdd01ef066bc6cf2", "tenant_id": None, "features": []}),
        ("Deprecated eval", {"constitutional_hash": "cdd01ef066bc6cf2", "tenant_id": "t1", "features": ["eval"]}),
    ]

    for name, input_data in tests:
        result = query("acgs/constitutional/allow", input_data)
        status = "PASS" if result.get("result") else "DENY"
        print(f"  {name}: {status}")

def test_rbac():
    """Test RBAC policy."""
    print("\n=== RBAC Policy Tests ===")

    tests = [
        ("Admin read", {"user": "admin", "role": "admin", "action": "read", "resource": "/api"}),
        ("Viewer delete", {"user": "bob", "role": "viewer", "action": "delete", "resource": "/api"}),
    ]

    for name, input_data in tests:
        result = query("acgs/rbac/allow_action", input_data)
        status = "ALLOW" if result.get("result") else "DENY"
        print(f"  {name}: {status}")

def test_ratelimit():
    """Test rate limiting policy."""
    print("\n=== Rate Limit Policy Tests ===")

    tests = [
        ("Within limit", {"client_id": "c1", "request_count": 50, "limit": 100, "window_seconds": 60}),
        ("Over limit", {"client_id": "c1", "request_count": 150, "limit": 100, "window_seconds": 60}),
    ]

    for name, input_data in tests:
        result = query("acgs/ratelimit/within_limits", input_data)
        status = "OK" if result.get("result") else "EXCEEDED"
        print(f"  {name}: {status}")

def main():
    print("=" * 60)
    print("ACGS-2 Interactive Policy Testing")
    print("=" * 60)

    # Check OPA health
    try:
        resp = requests.get(f"{OPA_URL}/health", timeout=2)
        print("✅ OPA is healthy")
    except:
        print("❌ OPA is not responding")
        sys.exit(1)

    test_constitutional()
    test_rbac()
    test_ratelimit()

    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)

if __name__ == "__main__":
    main()
```

---

## Video Tutorials

Prefer watching to reading? We've created video walkthroughs to guide you through ACGS-2.

### Available Videos

| Video | Duration | Description |
|-------|----------|-------------|
| **Quickstart Walkthrough** | 8 min | Complete walkthrough from clone to first policy evaluation |
| **Example Project Deep Dive** | 12 min | Building and understanding governance policies |
| **Jupyter Notebook Tutorial** | 10 min | Interactive policy experimentation with visualizations |

### Quickstart Walkthrough Video

<!-- VIDEO_PLACEHOLDER: Replace with actual video embed once recorded -->
<!-- Expected: YouTube embed or video player link -->

> **Video Coming Soon**: The quickstart walkthrough video is being produced.
>
> In the meantime, follow the written guide above, or view the [video script](./video-scripts/01-quickstart-walkthrough.md) to see what will be covered.

**What You'll Learn:**
- Setting up your development environment (2 min)
- Starting ACGS-2 services with Docker Compose (2 min)
- Evaluating your first governance policy (2 min)
- Testing policy violations and debugging (2 min)

### Video Production Status

| Video | Script | Recording | Editing | Published |
|-------|--------|-----------|---------|-----------|
| Quickstart Walkthrough | ✅ Complete | 🔄 Pending | ⏳ Waiting | ⏳ Waiting |
| Example Project Deep Dive | 🔄 In Progress | ⏳ Waiting | ⏳ Waiting | ⏳ Waiting |
| Jupyter Notebook Tutorial | 🔄 In Progress | ⏳ Waiting | ⏳ Waiting | ⏳ Waiting |

> **Contributors**: Want to help record these videos? See the [video scripts directory](./video-scripts/) for scripts and production guidelines.

---

## Next Steps

Congratulations! You've completed the ACGS-2 quickstart. Here's where to go next:

### Immediate Next Steps

1. **Explore Example Projects**
   - [Basic Policy Evaluation](../../examples/01-basic-policy-evaluation/)
   - [AI Model Approval](../../examples/02-ai-model-approval/)
   - [Data Access Control](../../examples/03-data-access-control/)

2. **Try Interactive Notebooks**
   - [Policy Experimentation](../../notebooks/01-policy-experimentation.ipynb)
   - [Governance Visualization](../../notebooks/02-governance-visualization.ipynb)

3. **Watch Video Tutorials**
   - [Quickstart Walkthrough](#video-tutorials) - 8-minute walkthrough of this guide
   - [Example Project Deep Dive](#video-tutorials) - Building real governance policies
   - [Jupyter Notebook Tutorial](#video-tutorials) - Interactive policy experimentation

### Learning Paths

| Path | Description | Time |
|------|-------------|------|
| **Policy Developer** | Learn Rego, write custom policies | 2-4 hours |
| **Integration Developer** | Integrate ACGS-2 with your applications | 4-8 hours |
| **Platform Operator** | Deploy and operate ACGS-2 | 8-16 hours |

### Documentation

| Resource | Description |
|----------|-------------|
| [Development Guide](../DEVELOPMENT.md) | Local development setup |
| [Architecture Docs](.././architecture/c4/) | C4 model architecture |
| [API Reference](../api/generated/api_reference.md) | Complete API documentation |
| [Security Guide](../security/) | Security implementation details |
| [Deployment Guide](../../src/infra/deploy/README.md) | Production deployment |

### Community & Support

- **GitHub Issues**: Report bugs or request features
- **Community Forum**: Discuss with other developers
- **Enterprise Support**: Contact enterprise@acgs2.org

---

## Troubleshooting

Having issues? Check these common problems and solutions.

### Quick Diagnosis

Run this script to diagnose common issues:

```bash
#!/bin/bash
echo "=== ACGS-2 Diagnostic Check ==="

# Check Docker
echo "1. Docker status:"
docker info > /dev/null 2>&1 && echo "   ✅ Docker is running" || echo "   ❌ Docker not running"

# Check containers
echo "2. Container status:"
docker compose -f docker-compose.dev.yml ps 2>/dev/null || echo "   ❌ No containers found"

# Check OPA
echo "3. OPA health:"
curl -s -o /dev/null -w "   Status: %{http_code}\n" http://localhost:8181/health 2>/dev/null || echo "   ❌ OPA not responding"

# Check Agent Bus
echo "4. Agent Bus health:"
curl -s -o /dev/null -w "   Status: %{http_code}\n" http://localhost:8000/health 2>/dev/null || echo "   ❌ Agent Bus not responding"

# Check Redis
echo "5. Redis:"
docker exec -it $(docker ps -qf "name=redis") redis-cli ping 2>/dev/null || echo "   ❌ Redis not responding"

echo ""
echo "=== Diagnosis Complete ==="
```

### Common Issues

For detailed troubleshooting, see [Troubleshooting Guide](./troubleshooting.md).

#### Docker Issues

| Problem | Solution |
|---------|----------|
| `Cannot connect to Docker daemon` | Start Docker Desktop or run `sudo systemctl start docker` |
| `Port already in use` | Stop conflicting service or change ports in `.env` |
| `Image pull failed` | Check internet connection, try `docker pull openpolicyagent/opa:latest` |

#### Service Issues

| Problem | Solution |
|---------|----------|
| OPA not responding | Check logs: `docker compose logs opa` |
| Agent Bus errors | Check logs: `docker compose logs agent-bus` |
| Redis connection failed | Verify Redis is running: `docker compose ps redis` |

#### Policy Issues

| Problem | Solution |
|---------|----------|
| Policy returns `undefined` | Check policy path matches package declaration |
| Syntax error in policy | Use `opa check file.rego` to validate |
| Input not recognized | Ensure input is wrapped in `{"input": {...}}` |

### Getting Help

1. **Check the logs**:
   ```bash
   docker compose -f docker-compose.dev.yml logs -f
   ```

2. **Verify configuration**:
   ```bash
   docker compose -f docker-compose.dev.yml config
   ```

3. **Reset the environment**:
   ```bash
   docker compose -f docker-compose.dev.yml down -v
   docker compose -f docker-compose.dev.yml up -d
   ```

---

## Feedback

We want to hear from you! Your feedback directly shapes the future of ACGS-2.

> **Target**: Help us maintain **< 30 minute** completion time and **> 4.0/5.0** satisfaction score

### Share Your Experience

After completing this quickstart, please take **2-3 minutes** to share your feedback:

| Action | Description |
|--------|-------------|
| **[📝 Submit Feedback Survey](../feedback.md)** | Comprehensive feedback form (recommended) |
| **[🐛 Report an Issue](https://github.com/dislovelhl/acgs2/issues/new?labels=documentation,quickstart)** | Report bugs or unclear sections |
| **[💡 Request Features](https://github.com/dislovelhl/acgs2/issues/new?labels=enhancement)** | Suggest new examples or improvements |

### Quick Feedback (30 seconds)

Rate your experience:

```
Overall Satisfaction: ___ / 5 (1=Poor, 5=Excellent)
Time to Complete:     ___ minutes
Hardest Section:      ________________
Would Recommend:      Yes / No / Maybe
```

**Submit via**: [GitHub Issue](https://github.com/dislovelhl/acgs2/issues/new?title=[Quickstart%20Feedback]&labels=feedback,quickstart) or email to docs@acgs2.org

### What We Measure

Your feedback helps us track:

| Metric | Target | Help Us By |
|--------|--------|------------|
| Time-to-First-Success | < 30 min | Report actual completion time |
| Developer Satisfaction | > 4.0/5.0 | Rate your experience honestly |
| Completion Rate | > 80% | Tell us if you got stuck |
| Issue Resolution | < 24 hours | Report technical problems |

### Contact

| Channel | Purpose | Response Time |
|---------|---------|---------------|
| **[Feedback Form](../feedback.md)** | Detailed feedback | Reviewed weekly |
| **docs@acgs2.org** | Documentation questions | 48-72 hours |
| **enterprise@acgs2.org** | Enterprise support | 24 hours |
| **GitHub Issues** | Bug reports | 24-48 hours |

---

## Appendix

### Quick Reference Card

```
ACGS-2 Quick Reference
======================

Services:
  OPA:       http://localhost:8181
  Agent Bus: http://localhost:8000
  Gateway:   http://localhost:8080
  Redis:     localhost:6379
  Kafka:     localhost:19092

Key Commands:
  Start:    docker compose -f docker-compose.dev.yml up -d
  Stop:     docker compose -f docker-compose.dev.yml down
  Logs:     docker compose -f docker-compose.dev.yml logs -f
  Status:   docker compose -f docker-compose.dev.yml ps

OPA Queries:
  Health:   curl http://localhost:8181/health
  Policies: curl http://localhost:8181/v1/policies
  Evaluate: curl -X POST http://localhost:8181/v1/data/{path} \
              -d '{"input": {...}}'

Constitutional Hash: cdd01ef066bc6cf2
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPA_URL` | http://opa:8181 | OPA service URL |
| `REDIS_URL` | redis://redis:6379/0 | Redis connection |
| `KAFKA_BOOTSTRAP` | kafka:29092 | Kafka bootstrap servers |
| `CONSTITUTIONAL_HASH` | cdd01ef066bc6cf2 | Constitutional hash |
| `MACI_STRICT_MODE` | true | Enable strict mode |
| `LOG_LEVEL` | INFO | Logging verbosity |

### Useful Links

- [OPA Documentation](https://www.openpolicyagent.org/docs/latest/)
- [Rego Language Reference](https://www.openpolicyagent.org/docs/latest/policy-language/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [ACGS-2 GitHub Repository](https://github.com/dislovelhl/acgs2)

---

**Constitutional Hash**: `cdd01ef066bc6cf2`
**Version**: 1.0.0
**Last Updated**: 2025-01-02

---

*Thank you for trying ACGS-2! We hope this quickstart guide was helpful. Don't forget to [share your feedback](../feedback.md)!*
