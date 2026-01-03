package acgs2.examples.basic_governance

# Basic Governance Policy
# Ensures AI responses are helpful, safe, and appropriately classified

# Default deny - everything is blocked unless explicitly allowed
default allow = false

# Allow helpful, safe content with high confidence
allow {
    input.intent.classification == "helpful"
    input.intent.confidence > 0.8
    not contains_harmful_content(input.content)
}

# Allow neutral content that passes safety checks
allow {
    input.intent.classification == "neutral"
    input.intent.confidence > 0.9
    not contains_harmful_content(input.content)
    not contains_inappropriate_content(input.content)
}

# Block harmful content
contains_harmful_content(content) {
    harmful_words := ["harmful", "dangerous", "illegal", "violent", "harm", "kill", "injure"]
    some word in harmful_words
    contains(lower(content), lower(word))
}

# Block inappropriate content
contains_inappropriate_content(content) {
    inappropriate_words := ["inappropriate", "offensive", "spam", "misinformation"]
    some word in inappropriate_words
    contains(lower(content), lower(word))
}

# Provide detailed feedback on violations
violations[violation] {
    not allow
    violation := get_violation_reason
}

get_violation_reason = reason {
    input.intent.classification != "helpful"
    input.intent.classification != "neutral"
    reason := sprintf("Invalid intent classification: %s", [input.intent.classification])
}

get_violation_reason = reason {
    input.intent.confidence <= 0.8
    reason := sprintf("Low confidence in intent classification: %.2f", [input.intent.confidence])
}

get_violation_reason = reason {
    contains_harmful_content(input.content)
    reason := "Content contains harmful or dangerous material"
}

get_violation_reason = reason {
    contains_inappropriate_content(input.content)
    reason := "Content contains inappropriate material"
}

# Metadata for policy analysis
policy_metadata = {
    "name": "Basic Governance Policy",
    "version": "1.0.0",
    "description": "Ensures AI responses are helpful, safe, and appropriately classified",
    "risk_level": "low",
    "categories": ["content_safety", "intent_classification"],
    "author": "ACGS-2 Example",
    "created": "2024-01-01"
}
