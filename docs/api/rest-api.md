--- Cursor Command: api/rest-api.md ---
# ACGS-2 REST API Documentation

Complete reference for all ACGS-2 REST API endpoints.

## 📋 Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Policy Registry API](#policy-registry-api)
4. [Agent Bus API](#agent-bus-api)
5. [Audit Service API](#audit-service-api)
6. [HITL Approvals API](#hitl-approvals-api)
7. [ML Governance API](#ml-governance-api)
8. [Error Handling](#error-handling)
9. [Rate Limiting](#rate-limiting)

## 🎯 Overview

ACGS-2 provides comprehensive REST APIs for all core services with enterprise-grade features.

### Base URLs

| Service | Base URL | Port | Description |
|---------|----------|------|-------------|
| Policy Registry | `http://localhost:8000` | 8000 | Policy management and evaluation |
| Agent Bus | `http://localhost:8080` | 8080 | Agent communication and coordination |
| Audit Service | `http://localhost:8084` | 8084 | Audit logging and compliance |
| HITL Approvals | `http://localhost:8081` | 8081 | Human-in-the-loop approvals |
| ML Governance | `http://localhost:8000` | 8000 | ML model governance |

### Common Headers

All requests must include:

```http
Content-Type: application/json
Authorization: Bearer <jwt-token>
X-Constitutional-Hash: cdd01ef066bc6cf2
X-Tenant-ID: <tenant-id>
X-Request-ID: <unique-request-id>
```

### Response Format

Standardized JSON response structure:

```json
{
  "status": "success|error",
  "data": { ... },
  "meta": {
    "request_id": "req-123",
    "timestamp": "2024-01-15T10:30:00Z",
    "constitutional_hash": "cdd01ef066bc6cf2",
    "processing_time_ms": 150
  },
  "errors": []
}
```

---

## 🔐 Authentication

### POST /api/v1/auth/login

Authenticate user and obtain JWT token.

**Request:**
```json
{
  "username": "user@example.com",
  "password": "password",
  "tenant_id": "optional-tenant-id"
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 3600,
    "refresh_token": "refresh-token-here",
    "user": {
      "id": "user-123",
      "username": "user@example.com",
      "roles": ["admin", "policy_manager"],
      "permissions": ["read", "write", "delete"]
    }
  }
}
```

### POST /api/v1/auth/refresh

Refresh an expired access token.

**Request:**
```json
{
  "refresh_token": "refresh-token-here"
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "access_token": "new-jwt-token",
    "token_type": "bearer",
    "expires_in": 3600
  }
}
```

### POST /api/v1/auth/logout

Invalidate the current session.

**Request:**
```json
{}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "message": "Logged out successfully"
  }
}
```

### GET /api/v1/auth/me

Get current user information.

**Response:**
```json
{
  "status": "success",
  "data": {
    "user": {
      "id": "user-123",
      "username": "user@example.com",
      "email": "user@example.com",
      "roles": ["admin"],
      "permissions": ["read", "write"],
      "tenant_id": "tenant-123",
      "last_login": "2024-01-15T10:30:00Z"
    }
  }
}
```

---

## 📋 Policy Registry API

### GET /api/v1/policies

List policies with optional filtering.

**Query Parameters:**
- `status` - active, draft, archived
- `type` - security, privacy, compliance, operational
- `severity` - critical, high, medium, low
- `limit` - max results (default: 50)
- `offset` - pagination offset (default: 0)
- `compliance_framework` - GDPR, CCPA, SOX, etc.

**Response:**
```json
{
  "status": "success",
  "data": {
    "policies": [
      {
        "id": "pol-123",
        "name": "Data Encryption Policy",
        "description": "Ensures all sensitive data is encrypted",
        "type": "security",
        "severity": "high",
        "status": "active",
        "compliance_frameworks": ["GDPR", "CCPA"],
        "rules": [
          {
            "id": "rule-456",
            "name": "Encryption Required",
            "condition": "resource.sensitivity == 'high'",
            "action": "encrypt",
            "severity": "high",
            "enabled": true
          }
        ],
        "created_at": "2024-01-15T10:30:00Z",
        "updated_at": "2024-01-15T10:30:00Z",
        "created_by": "user-123"
      }
    ],
    "pagination": {
      "total": 150,
      "limit": 50,
      "offset": 0,
      "has_more": true
    }
  }
}
```

### POST /api/v1/policies

Create a new policy.

**Request:**
```json
{
  "name": "Data Privacy Policy",
  "description": "Comprehensive data privacy governance",
  "type": "privacy",
  "severity": "high",
  "compliance_frameworks": ["GDPR", "CCPA"],
  "rules": [
    {
      "name": "PII Encryption",
      "condition": "resource.type == 'pii'",
      "action": "encrypt",
      "severity": "critical",
      "enabled": true,
      "parameters": {
        "algorithm": "AES-256",
        "key_rotation_days": 90
      }
    }
  ],
  "tags": ["privacy", "encryption", "gdpr"]
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "policy": {
      "id": "pol-456",
      "name": "Data Privacy Policy",
      "status": "draft",
      "created_at": "2024-01-15T10:30:00Z",
      "created_by": "user-123"
    }
  }
}
```

### GET /api/v1/policies/{id}

Get a specific policy by ID.

**Response:**
```json
{
  "status": "success",
  "data": {
    "policy": {
      "id": "pol-123",
      "name": "Data Encryption Policy",
      "description": "Ensures all sensitive data is encrypted",
      "type": "security",
      "severity": "high",
      "status": "active",
      "rules": [...],
      "compliance_frameworks": ["GDPR"],
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T11:00:00Z",
      "created_by": "user-123",
      "updated_by": "user-123"
    }
  }
}
```

### PUT /api/v1/policies/{id}

Update an existing policy.

**Request:**
```json
{
  "name": "Updated Data Encryption Policy",
  "description": "Enhanced encryption requirements",
  "rules": [
    {
      "id": "rule-456",
      "name": "Advanced Encryption Required",
      "condition": "resource.sensitivity == 'high' || resource.type == 'pii'",
      "action": "encrypt",
      "severity": "critical",
      "enabled": true
    }
  ]
}
```

### DELETE /api/v1/policies/{id}

Delete a policy (soft delete - marks as archived).

**Response:**
```json
{
  "status": "success",
  "data": {
    "message": "Policy archived successfully",
    "policy_id": "pol-123"
  }
}
```

### POST /api/v1/policies/{id}/validate

Validate a policy for syntax and logic errors.

**Response:**
```json
{
  "status": "success",
  "data": {
    "valid": true,
    "warnings": [],
    "errors": []
  }
}
```

### POST /api/v1/policies/{id}/activate

Activate a draft policy.

**Response:**
```json
{
  "status": "success",
  "data": {
    "policy_id": "pol-123",
    "status": "active",
    "activated_at": "2024-01-15T11:00:00Z",
    "activated_by": "user-123"
  }
}
```

### POST /api/v1/policies/evaluate

Evaluate a resource against active policies.

**Request:**
```json
{
  "resource": {
    "id": "res-123",
    "type": "user_data",
    "sensitivity": "high",
    "owner": "user-456",
    "location": "us-west-2"
  },
  "action": "read",
  "context": {
    "user_id": "user-789",
    "ip_address": "192.168.1.100",
    "user_agent": "Mozilla/5.0..."
  }
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "decision": "allow",
    "policies_applied": [
      {
        "policy_id": "pol-123",
        "policy_name": "Data Encryption Policy",
        "rules_matched": ["rule-456"],
        "severity": "high"
      }
    ],
    "obligations": [
      {
        "action": "encrypt",
        "parameters": {
          "algorithm": "AES-256"
        }
      }
    ],
    "advice": [
      {
        "type": "warning",
        "message": "Resource contains PII data"
      }
    ]
  }
}
```

---

## 🤖 Agent Bus API

### GET /api/v1/agents

List registered agents.

**Query Parameters:**
- `status` - active, busy, offline
- `type` - coder, analyst, security, architect, researcher
- `capability` - specific capability filter
- `limit` - max results (default: 50)

**Response:**
```json
{
  "status": "success",
  "data": {
    "agents": [
      {
        "id": "agent-123",
        "name": "Backend Developer",
        "type": "coder",
        "status": "active",
        "capabilities": ["python", "api", "database"],
        "resource_requirements": {
          "cpu": "2000m",
          "memory": "4Gi"
        },
        "current_task": null,
        "tasks_completed": 45,
        "success_rate": 0.98,
        "registered_at": "2024-01-15T10:30:00Z",
        "last_heartbeat": "2024-01-15T11:00:00Z"
      }
    ],
    "pagination": {
      "total": 12,
      "limit": 50,
      "offset": 0
    }
  }
}
```

### POST /api/v1/agents

Register a new agent.

**Request:**
```json
{
  "name": "Content Moderation Agent",
  "description": "AI-powered content moderation",
  "type": "analyst",
  "capabilities": ["text_analysis", "image_recognition", "sentiment_analysis"],
  "resource_requirements": {
    "cpu": "4000m",
    "memory": "8Gi",
    "gpu": "1"
  },
  "max_concurrency": 5,
  "health_check_interval": 30
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "agent": {
      "id": "agent-456",
      "name": "Content Moderation Agent",
      "status": "active",
      "api_key": "agent-key-789",
      "registered_at": "2024-01-15T11:00:00Z"
    }
  }
}
```

### GET /api/v1/agents/{id}

Get agent details.

**Response:**
```json
{
  "status": "success",
  "data": {
    "agent": {
      "id": "agent-123",
      "name": "Backend Developer",
      "type": "coder",
      "status": "active",
      "capabilities": ["python", "api", "database"],
      "performance_metrics": {
        "tasks_completed": 45,
        "success_rate": 0.98,
        "average_task_time": 180,
        "uptime_percentage": 99.7
      },
      "current_workload": 0,
      "last_task_completed": "2024-01-15T10:45:00Z"
    }
  }
}
```

### PUT /api/v1/agents/{id}

Update agent configuration.

**Request:**
```json
{
  "capabilities": ["python", "api", "database", "graphql"],
  "max_concurrency": 10,
  "resource_requirements": {
    "cpu": "3000m",
    "memory": "6Gi"
  }
}
```

### DELETE /api/v1/agents/{id}

Deregister an agent.

**Response:**
```json
{
  "status": "success",
  "data": {
    "message": "Agent deregistered successfully",
    "agent_id": "agent-123"
  }
}
```

### POST /api/v1/agents/{id}/heartbeat

Send agent heartbeat for health monitoring.

**Request:**
```json
{
  "status": "active",
  "health_score": 0.95,
  "current_tasks": 2,
  "resource_usage": {
    "cpu_percent": 65,
    "memory_mb": 2048,
    "disk_mb": 512
  },
  "metrics": {
    "requests_processed": 150,
    "average_response_time": 250,
    "error_count": 2
  }
}
```

### GET /api/v1/agents/{id}/tasks

Get agent's task history.

**Query Parameters:**
- `status` - completed, failed, in_progress
- `limit` - max results (default: 20)
- `since` - ISO date string

**Response:**
```json
{
  "status": "success",
  "data": {
    "tasks": [
      {
        "id": "task-123",
        "type": "code_review",
        "status": "completed",
        "started_at": "2024-01-15T10:30:00Z",
        "completed_at": "2024-01-15T10:45:00Z",
        "duration_seconds": 900,
        "result": "success",
        "metrics": {
          "files_reviewed": 12,
          "issues_found": 3,
          "lines_of_code": 1250
        }
      }
    ]
  }
}
```

### POST /api/v1/messages

Send a message through the agent bus.

**Request:**
```json
{
  "message_type": "task_assignment",
  "content": {
    "task_id": "task-123",
    "task_type": "code_review",
    "parameters": {
      "repository": "https://github.com/org/repo",
      "branch": "main",
      "files": ["src/**/*.py"]
    }
  },
  "from_agent": "coordinator",
  "to_agent": "agent-456",
  "priority": "high",
  "correlation_id": "corr-789"
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "message_id": "msg-123",
    "status": "delivered",
    "delivered_at": "2024-01-15T11:00:00Z"
  }
}
```

---

## 📊 Audit Service API

### GET /api/v1/audit/events

Query audit events with advanced filtering.

**Query Parameters:**
- `start_date` - ISO date string
- `end_date` - ISO date string
- `event_type` - policy_evaluation, authentication, agent_action, etc.
- `severity` - critical, high, medium, low, info
- `user_id` - specific user
- `resource_id` - specific resource
- `limit` - max results (default: 100)
- `offset` - pagination offset

**Response:**
```json
{
  "status": "success",
  "data": {
    "events": [
      {
        "id": "evt-123",
        "timestamp": "2024-01-15T10:30:00Z",
        "event_type": "policy_evaluation",
        "severity": "medium",
        "user_id": "user-456",
        "resource_id": "res-789",
        "action": "read",
        "decision": "allow",
        "policies_applied": ["pol-123"],
        "context": {
          "ip_address": "192.168.1.100",
          "user_agent": "ACGS2-SDK/1.0",
          "tenant_id": "tenant-123"
        },
        "metadata": {
          "processing_time_ms": 45,
          "rules_evaluated": 12
        }
      }
    ],
    "pagination": {
      "total": 1250,
      "limit": 100,
      "offset": 0,
      "has_more": true
    }
  }
}
```

### POST /api/v1/audit/events

Manually log an audit event (admin only).

**Request:**
```json
{
  "event_type": "manual_entry",
  "severity": "info",
  "description": "Manual security review completed",
  "user_id": "user-123",
  "resource_id": "review-456",
  "metadata": {
    "review_type": "quarterly_audit",
    "findings_count": 0
  }
}
```

### GET /api/v1/audit/events/{id}

Get detailed audit event information.

**Response:**
```json
{
  "status": "success",
  "data": {
    "event": {
      "id": "evt-123",
      "timestamp": "2024-01-15T10:30:00Z",
      "event_type": "policy_evaluation",
      "severity": "medium",
      "details": {
        "user_id": "user-456",
        "resource": {
          "id": "res-789",
          "type": "user_data",
          "sensitivity": "high"
        },
        "action": "read",
        "decision": "allow",
        "policies_applied": [
          {
            "id": "pol-123",
            "name": "Data Privacy Policy",
            "rules_matched": ["rule-456"]
          }
        ]
      },
      "context": {
        "ip_address": "192.168.1.100",
        "user_agent": "ACGS2-SDK/1.0",
        "correlation_id": "corr-789"
      }
    }
  }
}
```

### GET /api/v1/audit/reports/compliance

Generate compliance reports.

**Query Parameters:**
- `framework` - GDPR, CCPA, SOX, HIPAA, etc.
- `period` - last_week, last_month, last_quarter, custom
- `start_date` - for custom period
- `end_date` - for custom period
- `format` - json, pdf, csv

**Response:**
```json
{
  "status": "success",
  "data": {
    "report": {
      "framework": "GDPR",
      "period": "last_month",
      "generated_at": "2024-01-15T11:00:00Z",
      "overall_score": 94.5,
      "sections": [
        {
          "name": "Data Protection",
          "score": 96.2,
          "findings": [
            {
              "rule": "Article 25 - Data Protection by Design",
              "status": "compliant",
              "evidence": "All policies include data minimization principles"
            }
          ]
        },
        {
          "name": "Consent Management",
          "score": 89.3,
          "findings": [
            {
              "rule": "Article 7 - Consent",
              "status": "partial",
              "issues": ["Some legacy data lacks explicit consent"]
            }
          ]
        }
      ],
      "recommendations": [
        {
          "priority": "high",
          "description": "Implement consent management for legacy data",
          "deadline": "2024-02-15"
        }
      ]
    }
  }
}
```

### GET /api/v1/audit/metrics

Get audit metrics and statistics.

**Query Parameters:**
- `period` - last_hour, last_day, last_week, last_month
- `group_by` - event_type, severity, user, resource_type

**Response:**
```json
{
  "status": "success",
  "data": {
    "metrics": {
      "period": "last_week",
      "total_events": 15420,
      "events_by_type": {
        "policy_evaluation": 12890,
        "authentication": 1830,
        "agent_action": 520,
        "api_call": 180
      },
      "events_by_severity": {
        "critical": 12,
        "high": 145,
        "medium": 2340,
        "low": 8760,
        "info": 4163
      },
      "top_users": [
        {"user_id": "user-123", "event_count": 1250},
        {"user_id": "user-456", "event_count": 890}
      ],
      "anomaly_detection": {
        "unusual_activity_detected": false,
        "baseline_deviation": 0.05
      }
    }
  }
}
```

---

## 👤 HITL Approvals API

### GET /api/v1/approvals

List pending approvals requiring human review.

**Query Parameters:**
- `status` - pending, approved, rejected, expired
- `type` - policy_violation, high_risk_action, compliance_issue
- `priority` - critical, high, medium, low
- `assignee` - specific user ID
- `limit` - max results (default: 50)

**Response:**
```json
{
  "status": "success",
  "data": {
    "approvals": [
      {
        "id": "apr-123",
        "type": "policy_violation",
        "title": "High-risk data access request",
        "description": "Request to access PII data without proper justification",
        "priority": "high",
        "status": "pending",
        "requestor": {
          "id": "user-456",
          "name": "John Doe",
          "department": "Engineering"
        },
        "resource": {
          "id": "res-789",
          "type": "user_data",
          "sensitivity": "high"
        },
        "policies_violated": ["pol-123"],
        "created_at": "2024-01-15T10:30:00Z",
        "expires_at": "2024-01-16T10:30:00Z",
        "escalation_level": 1
      }
    ],
    "pagination": {
      "total": 25,
      "pending": 18,
      "limit": 50
    }
  }
}
```

### POST /api/v1/approvals/{id}/review

Submit a review decision for an approval request.

**Request:**
```json
{
  "decision": "approved",
  "comments": "Approved based on legitimate business need and proper safeguards in place",
  "justification": "Requestor provided valid business case and data handling procedures",
  "approver_role": "privacy_officer",
  "escalation_reason": null
}
```

**Decision Options:**
- `approved` - Approve the request
- `rejected` - Deny the request
- `escalate` - Send to higher authority
- `request_info` - Request additional information

**Response:**
```json
{
  "status": "success",
  "data": {
    "approval": {
      "id": "apr-123",
      "status": "approved",
      "reviewed_by": "user-123",
      "reviewed_at": "2024-01-15T11:00:00Z",
      "decision": "approved",
      "comments": "Approved based on legitimate business need",
      "processing_time_minutes": 30
    }
  }
}
```

### GET /api/v1/approvals/{id}

Get detailed approval request information.

**Response:**
```json
{
  "status": "success",
  "data": {
    "approval": {
      "id": "apr-123",
      "type": "policy_violation",
      "status": "pending",
      "details": {
        "requestor": {
          "id": "user-456",
          "name": "John Doe",
          "role": "Data Scientist",
          "department": "Analytics"
        },
        "resource": {
          "id": "res-789",
          "type": "customer_data",
          "description": "Customer purchase history and preferences",
          "sensitivity": "high",
          "data_classification": "PII"
        },
        "action": {
          "type": "export",
          "destination": "analysis_environment",
          "retention_period": "30_days"
        },
        "policies_violated": [
          {
            "id": "pol-123",
            "name": "Data Export Policy",
            "violation_reason": "Export destination not pre-approved"
          }
        ]
      },
      "context": {
        "business_case": "Customer churn analysis for Q1 marketing campaign",
        "data_handling_procedures": "Data will be anonymized after analysis",
        "alternative_solutions": ["Use aggregated data", "Work in secure environment"]
      },
      "timeline": {
        "created_at": "2024-01-15T10:30:00Z",
        "expires_at": "2024-01-16T10:30:00Z",
        "escalated_at": null,
        "last_reminder": null
      },
      "approvers": [
        {
          "level": 1,
          "role": "manager",
          "assignee": "user-789",
          "status": "pending",
          "assigned_at": "2024-01-15T10:30:00Z"
        }
      ]
    }
  }
}
```

### POST /api/v1/approvals/{id}/escalate

Escalate an approval to the next level.

**Request:**
```json
{
  "reason": "Policy complexity requires senior review",
  "additional_context": "Request involves cross-departmental data sharing",
  "urgency": "high"
}
```

### GET /api/v1/approvals/metrics

Get approval workflow metrics.

**Response:**
```json
{
  "status": "success",
  "data": {
    "metrics": {
      "total_requests": 1250,
      "pending_approvals": 45,
      "average_approval_time": 4.2,
      "approval_rate": 0.87,
      "escalation_rate": 0.12,
      "by_type": {
        "policy_violation": 850,
        "high_risk_action": 320,
        "compliance_issue": 80
      },
      "by_priority": {
        "critical": 25,
        "high": 120,
        "medium": 350,
        "low": 755
      }
    }
  }
}
```

---

## 🤖 ML Governance API

### GET /api/v1/models

List registered ML models.

**Query Parameters:**
- `status` - active, inactive, deprecated
- `type` - classification, regression, clustering, generation
- `risk_level` - low, medium, high, critical
- `compliance_status` - compliant, non_compliant, under_review

**Response:**
```json
{
  "status": "success",
  "data": {
    "models": [
      {
        "id": "mdl-123",
        "name": "Fraud Detection Model",
        "version": "2.1.0",
        "type": "classification",
        "status": "active",
        "risk_level": "high",
        "compliance_status": "compliant",
        "framework": "tensorflow",
        "metrics": {
          "accuracy": 0.94,
          "precision": 0.89,
          "recall": 0.91,
          "f1_score": 0.90
        },
        "governance": {
          "bias_assessment": "completed",
          "fairness_score": 0.92,
          "explainability": "lime_shap",
          "data_lineage": "tracked"
        },
        "created_at": "2024-01-15T10:30:00Z",
        "last_deployed": "2024-01-15T11:00:00Z"
      }
    ]
  }
}
```

### POST /api/v1/models

Register a new ML model.

**Request:**
```json
{
  "name": "Customer Sentiment Analyzer",
  "version": "1.0.0",
  "type": "classification",
  "framework": "pytorch",
  "description": "Analyzes customer feedback sentiment",
  "risk_level": "medium",
  "training_data": {
    "source": "customer_feedback_db",
    "size": 100000,
    "features": ["text", "rating", "category"],
    "labels": ["positive", "negative", "neutral"]
  },
  "metrics": {
    "accuracy": 0.87,
    "precision": 0.85,
    "recall": 0.88
  },
  "governance_requirements": {
    "bias_assessment_required": true,
    "explainability_required": true,
    "data_lineage_required": true,
    "human_review_required": false
  }
}
```

### GET /api/v1/models/{id}

Get model details and governance information.

**Response:**
```json
{
  "status": "success",
  "data": {
    "model": {
      "id": "mdl-123",
      "name": "Fraud Detection Model",
      "governance": {
        "bias_assessment": {
          "status": "completed",
          "score": 0.08,
          "protected_attributes": ["age", "gender", "location"],
          "recommendations": ["Monitor for location-based bias"]
        },
        "fairness_metrics": {
          "demographic_parity": 0.95,
          "equal_opportunity": 0.92,
          "disparate_impact": 1.02
        },
        "explainability": {
          "method": "shap",
          "feature_importance": {
            "transaction_amount": 0.35,
            "merchant_category": 0.28,
            "time_of_day": 0.22
          }
        }
      },
      "deployments": [
        {
          "environment": "production",
          "version": "2.1.0",
          "deployed_at": "2024-01-15T11:00:00Z",
          "status": "active"
        }
      ]
    }
  }
}
```

### POST /api/v1/models/{id}/assess

Request governance assessment for a model.

**Request:**
```json
{
  "assessment_type": "comprehensive",
  "priority": "high",
  "parameters": {
    "bias_threshold": 0.1,
    "fairness_metrics": ["demographic_parity", "equal_opportunity"],
    "explainability_method": "lime"
  }
}
```

### GET /api/v1/models/{id}/predictions

Get model prediction audit trail.

**Query Parameters:**
- `start_date` - ISO date string
- `end_date` - ISO date string
- `decision` - approved, rejected, flagged
- `confidence_threshold` - minimum confidence score

**Response:**
```json
{
  "status": "success",
  "data": {
    "predictions": [
      {
        "id": "pred-123",
        "timestamp": "2024-01-15T11:30:00Z",
        "input_features": {
          "transaction_amount": 1250.00,
          "merchant_category": "online_retail"
        },
        "prediction": {
          "class": "fraudulent",
          "confidence": 0.89,
          "probabilities": {
            "legitimate": 0.11,
            "fraudulent": 0.89
          }
        },
        "decision": "flagged",
        "reason": "High-value transaction with unusual merchant category",
        "reviewed_by": "user-456",
        "review_decision": "confirmed"
      }
    ]
  }
}
```

---

## ❌ Error Handling

### Error Response Format

```json
{
  "status": "error",
  "data": null,
  "meta": {
    "request_id": "req-123",
    "timestamp": "2024-01-15T10:30:00Z"
  },
  "errors": [
    {
      "code": "VALIDATION_ERROR",
      "message": "Invalid policy rule syntax",
      "field": "rules[0].condition",
      "details": {
        "expected": "valid rego syntax",
        "received": "invalid syntax"
      }
    }
  ]
}
```

### Common Error Codes

| Code | Description | HTTP Status |
|------|-------------|-------------|
| `AUTHENTICATION_ERROR` | Invalid or missing credentials | 401 |
| `AUTHORIZATION_ERROR` | Insufficient permissions | 403 |
| `VALIDATION_ERROR` | Invalid request data | 400 |
| `NOT_FOUND_ERROR` | Resource not found | 404 |
| `CONFLICT_ERROR` | Resource conflict | 409 |
| `RATE_LIMIT_ERROR` | Too many requests | 429 |
| `QUOTA_EXCEEDED_ERROR` | Resource quota exceeded | 429 |
| `SERVICE_UNAVAILABLE` | Service temporarily unavailable | 503 |

### Error Categories

#### Client Errors (4xx)
- **400 Bad Request**: Malformed request syntax
- **401 Unauthorized**: Authentication required
- **403 Forbidden**: Authorization failed
- **404 Not Found**: Resource doesn't exist
- **409 Conflict**: Resource state conflict
- **429 Too Many Requests**: Rate limit exceeded

#### Server Errors (5xx)
- **500 Internal Server Error**: Unexpected server error
- **502 Bad Gateway**: Invalid response from upstream
- **503 Service Unavailable**: Service temporarily down
- **504 Gateway Timeout**: Request timeout

---

## 🚦 Rate Limiting

### Rate Limit Headers

All responses include rate limiting information:

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 950
X-RateLimit-Reset: 1642156800
X-RateLimit-Retry-After: 60
```

### Rate Limit Policies

#### By Endpoint Type
- **Read Operations**: 1000 requests/minute
- **Write Operations**: 500 requests/minute
- **Bulk Operations**: 100 requests/minute
- **Administrative**: 200 requests/minute

#### By User Type
- **Standard Users**: Base rate limits
- **Power Users**: 2x rate limits
- **Administrators**: 5x rate limits
- **Service Accounts**: Custom limits

### Rate Limit Exceeded Response

```json
{
  "status": "error",
  "data": null,
  "meta": {
    "request_id": "req-123",
    "timestamp": "2024-01-15T10:30:00Z"
  },
  "errors": [
    {
      "code": "RATE_LIMIT_ERROR",
      "message": "Rate limit exceeded",
      "details": {
        "limit": 1000,
        "remaining": 0,
        "reset_time": "2024-01-15T10:31:00Z",
        "retry_after_seconds": 30
      }
    }
  ]
}
```

### Handling Rate Limits

#### Exponential Backoff
```javascript
async function makeRequest(retryCount = 0) {
  try {
    const response = await fetch('/api/v1/policies');
    return response.json();
  } catch (error) {
    if (error.status === 429) {
      const retryAfter = error.headers.get('X-RateLimit-Retry-After');
      const delay = Math.min(1000 * Math.pow(2, retryCount), 30000);
      await new Promise(resolve => setTimeout(resolve, delay));
      return makeRequest(retryCount + 1);
    }
    throw error;
  }
}
```

#### Proactive Rate Limiting
```typescript
class RateLimiter {
  private requests: number[] = [];

  canMakeRequest(): boolean {
    const now = Date.now();
    // Remove requests older than 1 minute
    this.requests = this.requests.filter(time => now - time < 60000);
    return this.requests.length < 900; // 90% of 1000 limit
  }

  recordRequest(): void {
    this.requests.push(Date.now());
  }
}
```

---

**ACGS-2 REST API**: Complete Enterprise API Reference for Constitutional AI Governance

**Constitutional Hash: cdd01ef066bc6cf2** ✅
