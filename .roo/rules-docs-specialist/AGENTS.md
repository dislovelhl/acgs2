# Documentation Specialist Rules — ACGS-2

> **Goal**: Create clear, scannable, actionable documentation that accelerates developer onboarding.

---

## ⚡ Quick Rules

| Always                                 | Never                              |
| -------------------------------------- | ---------------------------------- |
| Include `cdd01ef066bc6cf2` in examples | Omit constitutional hash from code |
| Show copy-pasteable snippets           | Describe code without showing it   |
| Lead with the most common use case     | Start with edge cases              |
| Use tables for structured data         | Wall of text for comparisons       |
| Validate all links before committing   | Leave broken cross-references      |

---

## 📝 Documentation Templates

### API Endpoint Template

```markdown
## `POST /api/messages/send`

**Purpose**: Send a message between agents

**Constitutional Hash**: `cdd01ef066bc6cf2` (required)

### Request

| Field                 | Type   | Required | Description                |
| --------------------- | ------ | -------- | -------------------------- |
| `sender_id`           | string | ✅       | Agent sending message      |
| `recipient_id`        | string | ✅       | Target agent               |
| `content`             | string | ✅       | Message payload            |
| `constitutional_hash` | string | ✅       | Must be `cdd01ef066bc6cf2` |

### Response

| Status | Meaning                          |
| ------ | -------------------------------- |
| 200    | Success                          |
| 400    | Invalid request                  |
| 403    | Constitutional validation failed |

### Example

\`\`\`python
await bus.send_message(
sender_id="agent-1",
recipient_id="agent-2",
content="Hello",
constitutional_hash="cdd01ef066bc6cf2"
)
\`\`\`
```

### Feature Documentation Template

```markdown
## [Feature Name]

> **TL;DR**: [One sentence summary]

### When to Use

- Scenario 1
- Scenario 2

### Quick Start

\`\`\`python

# Minimal working example with constitutional_hash

\`\`\`

### Configuration

| Option | Default | Description |
| ------ | ------- | ----------- |

### Common Patterns

1. Pattern A: [code]
2. Pattern B: [code]

### Gotchas

⚠️ [Critical gotcha with solution]

### Related

- [Link to related doc]
```

---

## 🎯 Decision Trees for Documentation

### What Type of Doc?

```
Is it a single API endpoint?     → API reference with request/response tables
Is it a workflow or process?     → Step-by-step guide with diagrams
Is it a concept explanation?     → Architecture doc with diagrams
Is it a problem-solution pair?   → Troubleshooting entry
Is it configuration?             → Config reference with defaults table

```

### Where Should It Go?

```
General user guide       → docs/user-guides/
API reference            → docs/api/
Architecture decision    → docs/adr/
Deployment               → docs/deployment/
Troubleshooting          → Add to existing troubleshooting sections
Quick reference          → Add to CLAUDE.md or AGENTS.md
```

---

## 📊 Formatting Standards

### Tables (Use For)

- Configuration options with defaults
- API request/response fields

- Feature comparisons
- Role permissions (MACI)
- Error codes and meanings

### Code Blocks (Requirements)

```python
# ✅ ALWAYS include:
# 1. Constitutional hash where applicable
# 2. Import statements
# 3. Async/await if async operation
# 4. Error handling for non-trivial examples

from enhanced_agent_bus import EnhancedAgentBus
from enhanced_agent_bus.exceptions import ConstitutionalHashMismatchError

try:
    bus = EnhancedAgentBus()
    await bus.start()
    await bus.send_message(
        content="Hello",
        constitutional_hash="cdd01ef066bc6cf2"  # REQUIRED

    )
except ConstitutionalHashMismatchError as e:
    logger.error(f"Hash validation failed: {e}")
```

### Diagrams (ASCII Preferred)

```
Agent → Bus → Validation → [Score >= 0.8?]
                              ├── Yes → Deliberation
                              └── No  → Fast Lane

```

---

## 🔐 Constitutional Compliance in Docs

### Mandatory Hash Inclusion

Every code example involving messages, agents, or bus operations MUST include:

```python
constitutional_hash="cdd01ef066bc6cf2"

```

### Security-First Order

When documenting features, lead with:

1. Security requirements
2. Constitutional validation
3. Then functional details

### Example Security Section

```markdown
## Security

**Constitutional Hash**: All operations require `cdd01ef066bc6cf2`

| Scenario      | Behavior                          |
| ------------- | --------------------------------- |
| Hash missing  | Request rejected (400)            |
| Hash mismatch | `ConstitutionalHashMismatchError` |
| Hash valid    | Proceed to next step              |
```

---

## 🏗️ Architecture Documentation

### Multi-Backend Explanation Pattern

```markdown
## Message Bus Backend

| Backend          | Use Case                   | Performance   |
| ---------------- | -------------------------- | ------------- |
| Python (default) | Standard workloads         | Baseline      |
| Rust (optional)  | High-throughput (>10K RPS) | 10-50x faster |

### Fallback Behavior

If Rust is unavailable, Python backend is used automatically.
No code changes required.
```

### Performance Trade-off Pattern

```markdown
## When to Use Rust Backend

| Scenario         | Recommendation                      |
| ---------------- | ----------------------------------- |
| <1K RPS          | Python (simpler deployment)         |
| 1K-10K RPS       | Python or Rust                      |
| >10K RPS         | Rust (required for latency targets) |
| Latency-critical | Rust                                |
```

---

## 🔄 Deliberation Layer Documentation

### Impact Scoring Section Pattern

```markdown
## Impact Scoring

Messages are scored 0.0-1.0 based on:
| Factor | Weight | Description |
|--------|--------|-------------|
| Semantic | 0.30 | Content analysis |
| Permission | 0.20 | Access scope |
| Drift | 0.15 | Deviation from norms |

**Threshold**: Score ≥ 0.8 triggers deliberation
```

### HITL Documentation Pattern

```markdown
## Human-in-the-Loop Approvals

### Flow

1. High-impact message detected (score ≥ 0.8)
2. Routed to deliberation queue
3. Human/AI review required
4. Approval → Delivery
5. Rejection → Logged + Blocked

### Timeout

Default: 5-10 minutes
Configurable via `DELIBERATION_TIMEOUT_SECONDS`
```

---

## 🏢 Multi-Tenant Documentation

### Tenant Isolation Pattern

```markdown
## Multi-Tenant Architecture

### Requirements

| Requirement        | Details                           |
| ------------------ | --------------------------------- |
| `tenant_id`        | Required on all messages          |
| Agent registration | Must register before send/receive |
| Security context   | Additional metadata per tenant    |

### Isolation Guarantee

Messages are segregated by `tenant_id`. Agent A in Tenant 1 cannot see Agent B in Tenant 2.
```

---

## 🛠️ Troubleshooting Documentation

### Problem-Solution Format

```markdown
## Troubleshooting

### Constitutional Hash Mismatch

**Symptom**: `ConstitutionalHashMismatchError` on all operations
**Cause**: Wrong hash value
**Solution**:
\`\`\`python

# Verify you're using the correct hash

CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2" # This exact value

\`\`\`

### Rust Backend Unavailable

**Symptom**: Warning about Rust backend, slower performance
**Cause**: Rust extension not built
**Solution**:
\`\`\`bash
cd enhanced_agent_bus/rust
cargo build --release

\`\`\`
**Note**: System works without Rust (Python fallback)
```

---

## ✅ Documentation Checklist

### Before Publishing

- [ ] Constitutional hash `cdd01ef066bc6cf2` in all code examples
- [ ] All code blocks have language specifiers
- [ ] Tables used for structured comparisons
- [ ] Links validated (internal and external)
- [ ] TL;DR at top of long documents
- [ ] Async/await correct in Python examples
- [ ] Error handling shown in non-trivial examples

### Quality Gates

- [ ] Can a new developer follow this in <5 minutes?
- [ ] Is the most common use case shown first?
- [ ] Are edge cases documented but not leading?
- [ ] Are copy-paste examples provided?

---

## 📁 Documentation Structure

```

docs/
├── user-guides/          # Step-by-step guides
├── api/                  # API reference (OpenAPI + examples)
│   └── specs/            # OpenAPI YAML files
├── architecture/         # System design docs

├── adr/                  # Architecture Decision Records
├── deployment/           # Deployment guides
│   ├── air-gapped/
│   ├── high-availability/
│   └── multi-region/
├── observability/        # Logging, metrics, tracing

├── security/             # Security docs
└── tutorials/            # Hands-on tutorials
```

---

## 🎨 Style Guide

### Voice

- Active voice: "The bus validates the hash" not "The hash is validated"
- Present tense: "Returns a message" not "Will return a message"
- Second person for guides: "You can configure..." not "One can configure..."

### Headings

- H1: Document title only
- H2: Major sections
- H3: Subsections
- H4+: Rarely needed; consider restructuring

### Lists

- Bullet for unordered items
- Numbers only when order matters
- Max 7 items before grouping

### Emphasis

- **Bold**: Key terms, warnings
- `code`: File names, functions, values
- _Italic_: Rarely (first use of technical term)
- ⚠️ Emoji: Warnings and visual anchors only
