package policies.rego.constitutional.pii

import future.keywords.contains
import future.keywords.if

# Basic PII detection patterns
email_pattern := `[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}`
# Simple SSN-like pattern for demonstration
ssn_pattern := `\\d{3}-\\d{2}-\\d{4}`

violations contains msg if {
    message := input.message.content
    regex.match(email_pattern, message)
    msg := "PII Detected: Message contains an email address."
}

violations contains msg if {
    message := input.message.content
    regex.match(ssn_pattern, message)
    msg := "PII Detected: Message contains a potential SSN."
}
