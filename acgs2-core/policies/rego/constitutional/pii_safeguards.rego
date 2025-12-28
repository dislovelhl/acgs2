package policies.rego.constitutional.pii

# Basic PII detection patterns
email_pattern := `[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}`
# Simple SSN-like pattern for demonstration
ssn_pattern := `\\d{3}-\\d{2}-\\d{4}`

violations[msg] {
    message := input.message.content
    re_match(email_pattern, message)
    msg := "PII Detected: Message contains an email address."
}

violations[msg] {
    message := input.message.content
    re_match(ssn_pattern, message)
    msg := "PII Detected: Message contains a potential SSN."
}
