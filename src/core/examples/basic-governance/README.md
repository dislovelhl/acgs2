# Basic Governance Example

A simple example showing how to implement content governance with ACGS-2. This example filters out harmful or inappropriate content while allowing helpful responses.

## What You'll Learn

- How to write basic Rego policies
- Intent classification integration
- Simple content filtering
- Policy testing and validation

## Project Structure

```
basic-governance/
├── policy.rego          # Governance policy
├── test_policy.py       # Python test script
├── requirements.txt     # Dependencies
└── README.md           # This file
```

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the example
python test_policy.py
```

## The Policy

The policy in `policy.rego` implements three rules:

1. **Intent Classification**: Ensures the AI intent is classified as "helpful"
2. **Content Safety**: Blocks responses containing harmful keywords
3. **Confidence Threshold**: Requires minimum confidence in intent classification

## Policy Logic

```rego
# Allow helpful, safe content with high confidence
allow {
    input.intent.classification == "helpful"
    input.intent.confidence > 0.8
    not contains_harmful_content(input.content)
}

# Block harmful content
contains_harmful_content(content) {
    harmful_words := ["harmful", "dangerous", "illegal", "violent"]
    some word in harmful_words
    contains(lower(content), lower(word))
}
```

## Testing

The example includes tests for:

- ✅ Allowed helpful content
- ❌ Blocked harmful content
- ❌ Blocked low-confidence intents
- ❌ Blocked unsafe content

## Expected Output

```
Testing Basic Governance Policy
===============================

✅ Test 1 PASSED: Helpful content allowed
✅ Test 2 PASSED: Harmful content blocked
✅ Test 3 PASSED: Low confidence blocked
✅ Test 4 PASSED: Mixed intent blocked

All tests passed! 🎉
```

## Next Steps

Try modifying the policy to:
- Add more content categories (spam, misinformation, etc.)
- Implement confidence-based escalation
- Add user role-based permissions
- Integrate with external content classifiers

## Related Examples

- [Content Moderation](../content-moderation/) - Advanced content filtering
- [Code Review Assistant](../code-review-assistant/) - Code quality governance
- [Financial Advice](../financial-advice/) - Domain-specific compliance
