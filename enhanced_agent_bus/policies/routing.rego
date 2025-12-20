package acgs.routing

import future.keywords.if
import future.keywords.in

# Default routing based on message type
destination := {
    "agent": default_agent_for_type[input.message.message_type],
    "priority": input.message.priority
} if {
    input.message.constitutional_hash == "cdd01ef066bc6cf2"
}

# High priority messages go to high-priority queue
destination := {
    "agent": "high_priority_handler",
    "priority": "high",
    "queue": "priority"
} if {
    input.message.priority in ["high", "critical"]
    input.message.constitutional_hash == "cdd01ef066bc6cf2"
}

# Governance requests go to deliberation layer
destination := {
    "agent": "deliberation_layer",
    "priority": "high",
    "queue": "governance"
} if {
    input.message.message_type == "governance_request"
    input.message.constitutional_hash == "cdd01ef066bc6cf2"
}

# Default agent mapping by message type
default_agent_for_type := {
    "command": "command_processor",
    "query": "query_handler",
    "event": "event_dispatcher",
    "notification": "notification_service"
}
