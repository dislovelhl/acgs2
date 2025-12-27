package acgs.compliance

import future.keywords.if

default compliant = true

# Check all compliance requirements
compliant if {
    has_constitutional_hash
    has_required_fields
    within_size_limits
    no_prohibited_content
}

has_constitutional_hash if {
    input.message.constitutional_hash == "cdd01ef066bc6cf2"
}

has_required_fields if {
    input.message.message_id
    input.message.from_agent
    input.message.to_agent
    input.message.message_type
}

within_size_limits if {
    count(input.message.content) < 10000  # Max 10KB message size
}

no_prohibited_content if {
    not contains_prohibited_terms
}

contains_prohibited_terms if {
    some term in prohibited_terms
    contains(lower(json.marshal(input.message.content)), term)
}

prohibited_terms := [
    "malicious",
    "exploit",
    "backdoor"
]

# Compliance violations
violations := [msg |
    not has_constitutional_hash
    msg := "Missing or invalid constitutional hash"
]

violations := [msg |
    not has_required_fields
    msg := "Missing required message fields"
]

violations := [msg |
    not within_size_limits
    msg := "Message size exceeds limits"
]

violations := [msg |
    contains_prohibited_terms
    msg := "Message contains prohibited content"
]
