# ACGS-2 Rego Policy Test Suite
# Constitutional Hash: cdd01ef066bc6cf2
#
# Comprehensive test suite for all ACGS-2 policies

package acgs.tests

import future.keywords.if
import data.acgs.constitutional
import data.acgs.agent_bus.authz
import data.acgs.deliberation

# Test Constitutional Policy

test_constitutional_valid_message if {
    input := {
        "message": {
            "message_id": "msg-123",
            "conversation_id": "conv-456",
            "from_agent": "agent-1",
            "to_agent": "agent-2",
            "message_type": "command",
            "content": {"action": "test"},
            "constitutional_hash": "cdd01ef066bc6cf2",
            "priority": 2,
            "tenant_id": "tenant-1",
            "created_at": "2025-12-17T10:00:00Z",
            "updated_at": "2025-12-17T10:00:00Z"
        },
        "context": {
            "agent_role": "worker",
            "tenant_id": "tenant-1",
            "multi_tenant_enabled": true
        }
    }

    constitutional.allow with input as input
}

test_constitutional_invalid_hash if {
    input := {
        "message": {
            "message_id": "msg-123",
            "conversation_id": "conv-456",
            "from_agent": "agent-1",
            "to_agent": "agent-2",
            "message_type": "command",
            "content": {"action": "test"},
            "constitutional_hash": "wrong-hash",
            "priority": 2,
            "tenant_id": "tenant-1",
            "created_at": "2025-12-17T10:00:00Z",
            "updated_at": "2025-12-17T10:00:00Z"
        },
        "context": {
            "agent_role": "worker",
            "tenant_id": "tenant-1",
            "multi_tenant_enabled": true
        }
    }

    not constitutional.allow with input as input
    count(constitutional.violations) > 0 with input as input
}

test_constitutional_missing_fields if {
    input := {
        "message": {
            "message_id": "msg-123",
            "content": {},
            "constitutional_hash": "cdd01ef066bc6cf2"
        },
        "context": {
            "agent_role": "worker"
        }
    }

    not constitutional.allow with input as input
}

test_constitutional_tenant_isolation if {
    input := {
        "message": {
            "message_id": "msg-123",
            "conversation_id": "conv-456",
            "from_agent": "agent-1",
            "to_agent": "agent-2",
            "message_type": "command",
            "content": {"action": "test"},
            "constitutional_hash": "cdd01ef066bc6cf2",
            "priority": 2,
            "tenant_id": "tenant-1",
            "created_at": "2025-12-17T10:00:00Z",
            "updated_at": "2025-12-17T10:00:00Z"
        },
        "context": {
            "agent_role": "worker",
            "tenant_id": "tenant-2",
            "multi_tenant_enabled": true
        }
    }

    not constitutional.allow with input as input
}

test_constitutional_priority_escalation if {
    input := {
        "message": {
            "message_id": "msg-123",
            "conversation_id": "conv-456",
            "from_agent": "agent-1",
            "to_agent": "agent-2",
            "message_type": "command",
            "content": {"action": "test"},
            "constitutional_hash": "cdd01ef066bc6cf2",
            "priority": 0,
            "tenant_id": "tenant-1",
            "created_at": "2025-12-17T10:00:00Z",
            "updated_at": "2025-12-17T10:00:00Z"
        },
        "context": {
            "agent_role": "worker",
            "tenant_id": "tenant-1",
            "multi_tenant_enabled": true
        }
    }

    not constitutional.allow with input as input
}

# Test Authorization Policy

test_authz_valid_coordinator if {
    input := {
        "agent": {
            "agent_id": "coord-1",
            "role": "coordinator",
            "status": "active",
            "tenant_id": "tenant-1"
        },
        "action": "send_message",
        "target": {
            "agent_id": "worker-1",
            "agent_type": "worker",
            "tenant_id": "tenant-1"
        },
        "context": {
            "current_rate": 50,
            "multi_tenant_enabled": true
        },
        "security_context": {
            "auth_token": "valid-token",
            "token_expiry": "2025-12-17T20:00:00Z"
        },
        "message_type": "command"
    }

    authz.allow with input as input
}

test_authz_system_admin_override if {
    input := {
        "agent": {
            "agent_id": "admin-1",
            "role": "system_admin",
            "status": "active",
            "tenant_id": "tenant-1"
        },
        "action": "constitutional_update",
        "target": {
            "agent_id": "system",
            "agent_type": "system",
            "tenant_id": "tenant-1"
        },
        "context": {
            "current_rate": 5,
            "multi_tenant_enabled": true
        },
        "security_context": {
            "auth_token": "admin-token",
            "token_expiry": "2025-12-17T20:00:00Z"
        },
        "message_type": "governance_request"
    }

    authz.allow with input as input
}

test_authz_unauthorized_action if {
    input := {
        "agent": {
            "agent_id": "guest-1",
            "role": "guest",
            "status": "active",
            "tenant_id": "tenant-1"
        },
        "action": "constitutional_update",
        "target": {
            "agent_id": "system",
            "agent_type": "system",
            "tenant_id": "tenant-1"
        },
        "context": {
            "current_rate": 5,
            "multi_tenant_enabled": true
        },
        "security_context": {
            "auth_token": "guest-token",
            "token_expiry": "2025-12-17T20:00:00Z"
        },
        "message_type": "governance_request"
    }

    not authz.allow with input as input
}

test_authz_rate_limit_exceeded if {
    input := {
        "agent": {
            "agent_id": "worker-1",
            "role": "worker",
            "status": "active",
            "tenant_id": "tenant-1"
        },
        "action": "send_message",
        "target": {
            "agent_id": "coord-1",
            "agent_type": "coordinator",
            "tenant_id": "tenant-1"
        },
        "context": {
            "current_rate": 250,
            "multi_tenant_enabled": true
        },
        "security_context": {
            "auth_token": "worker-token",
            "token_expiry": "2025-12-17T20:00:00Z"
        },
        "message_type": "query"
    }

    not authz.allow with input as input
}

test_authz_cross_tenant_denied if {
    input := {
        "agent": {
            "agent_id": "worker-1",
            "role": "worker",
            "status": "active",
            "tenant_id": "tenant-1"
        },
        "action": "send_message",
        "target": {
            "agent_id": "worker-2",
            "agent_type": "worker",
            "tenant_id": "tenant-2"
        },
        "context": {
            "current_rate": 10,
            "multi_tenant_enabled": true
        },
        "security_context": {
            "auth_token": "worker-token",
            "token_expiry": "2025-12-17T20:00:00Z"
        },
        "message_type": "query"
    }

    not authz.allow with input as input
}

# Test Deliberation Policy

test_deliberation_high_impact if {
    input := {
        "message": {
            "message_id": "msg-123",
            "message_type": "governance_request",
            "content": {"action": "policy_change"},
            "impact_score": 0.92,
            "constitutional_hash": "cdd01ef066bc6cf2",
            "tenant_id": "tenant-1"
        },
        "context": {
            "tenant_id": "tenant-1",
            "multi_tenant_enabled": true
        }
    }

    deliberation.route_to_deliberation with input as input
    deliberation.routing_decision.lane == "deliberation" with input as input
    deliberation.routing_decision.requires_human_review == true with input as input
}

test_deliberation_fast_lane if {
    input := {
        "message": {
            "message_id": "msg-123",
            "message_type": "heartbeat",
            "content": {"status": "healthy"},
            "impact_score": 0.1,
            "constitutional_hash": "cdd01ef066bc6cf2",
            "tenant_id": "tenant-1"
        },
        "context": {
            "tenant_id": "tenant-1",
            "multi_tenant_enabled": true
        }
    }

    not deliberation.route_to_deliberation with input as input
    deliberation.routing_decision.lane == "fast" with input as input
}

test_deliberation_high_risk_action if {
    input := {
        "message": {
            "message_id": "msg-123",
            "message_type": "command",
            "content": {"action": "constitutional_update"},
            "impact_score": 0.7,
            "constitutional_hash": "cdd01ef066bc6cf2",
            "tenant_id": "tenant-1"
        },
        "context": {
            "tenant_id": "tenant-1",
            "multi_tenant_enabled": true
        }
    }

    deliberation.route_to_deliberation with input as input
    deliberation.high_risk_action with input as input
}

test_deliberation_sensitive_content if {
    input := {
        "message": {
            "message_id": "msg-123",
            "message_type": "command",
            "content": {
                "action": "process_payment",
                "amount": 1000,
                "payment": "credit_card"
            },
            "impact_score": 0.6,
            "constitutional_hash": "cdd01ef066bc6cf2",
            "tenant_id": "tenant-1"
        },
        "context": {
            "tenant_id": "tenant-1",
            "multi_tenant_enabled": true
        }
    }

    deliberation.route_to_deliberation with input as input
    deliberation.sensitive_content_detected with input as input
}

test_deliberation_forced if {
    input := {
        "message": {
            "message_id": "msg-123",
            "message_type": "query",
            "content": {"force_deliberation": true},
            "impact_score": 0.3,
            "constitutional_hash": "cdd01ef066bc6cf2",
            "tenant_id": "tenant-1"
        },
        "context": {
            "tenant_id": "tenant-1",
            "multi_tenant_enabled": true
        }
    }

    deliberation.route_to_deliberation with input as input
    deliberation.forced_deliberation with input as input
}

test_deliberation_multi_agent_vote if {
    input := {
        "message": {
            "message_id": "msg-123",
            "message_type": "governance_request",
            "content": {"action": "policy_change"},
            "impact_score": 0.97,
            "constitutional_hash": "cdd01ef066bc6cf2",
            "tenant_id": "tenant-1"
        },
        "context": {
            "tenant_id": "tenant-1",
            "multi_tenant_enabled": true
        }
    }

    deliberation.routing_decision.requires_multi_agent_vote == true with input as input
}

test_deliberation_constitutional_risk if {
    input := {
        "message": {
            "message_id": "msg-123",
            "message_type": "command",
            "content": {
                "constitutional_hash": "malicious-hash"
            },
            "impact_score": 0.5,
            "constitutional_hash": "cdd01ef066bc6cf2",
            "tenant_id": "tenant-1"
        },
        "context": {
            "tenant_id": "tenant-1",
            "multi_tenant_enabled": true
        }
    }

    deliberation.route_to_deliberation with input as input
    deliberation.constitutional_risk_detected with input as input
}
