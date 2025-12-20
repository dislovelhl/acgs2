package acgs.constitutional

import future.keywords.if

default validate = false

# Validate constitutional hash presence and correctness
validate if {
    input.message.constitutional_hash == "cdd01ef066bc6cf2"
}

# Validate message structure
validate if {
    input.message.message_id
    input.message.from_agent
    input.message.to_agent
    input.message.constitutional_hash == "cdd01ef066bc6cf2"
}

# Return detailed validation result
allow := {
    "allow": validate,
    "reason": reason,
    "metadata": {
        "policy": "constitutional_validation",
        "version": "1.0.0"
    }
}

reason := "Valid constitutional hash and message structure" if validate
reason := sprintf("Invalid constitutional hash: %v", [input.message.constitutional_hash]) if {
    not validate
    input.message.constitutional_hash != "cdd01ef066bc6cf2"
}
reason := "Missing required message fields" if {
    not validate
    not input.message.message_id
}
