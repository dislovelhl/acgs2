# Constitutional Framework - User Guide

**Constitutional Hash: `cdd01ef066bc6cf2`**

The Constitutional Framework is the core governance system of ACGS-2, providing cryptographic verification, policy management, immutable audit trails, and multi-agent deliberation for AI governance decisions.

---

## Table of Contents

1. [Overview](#overview)
2. [Constitutional Hash](#constitutional-hash)
3. [Policy Registry](#policy-registry)
4. [Cryptographic Signatures](#cryptographic-signatures)
5. [Audit Ledger](#audit-ledger)
6. [Merkle Tree Verification](#merkle-tree-verification)
7. [Blockchain Integration](#blockchain-integration)
8. [Constitutional Retrieval System](#constitutional-retrieval-system)
9. [Multi-Agent Deliberation](#multi-agent-deliberation)
10. [Constraint Generation](#constraint-generation)
11. [Compliance Validation](#compliance-validation)
12. [Best Practices](#best-practices)

---

## Overview

The Constitutional Framework ensures:

- **Cryptographic Integrity**: All operations verified with hash `cdd01ef066bc6cf2`
- **Immutable Audit Trail**: Merkle tree-based audit logging
- **Policy Governance**: Version-controlled, signed policies
- **Deliberation Process**: Multi-agent review for high-risk decisions
- **Blockchain Ready**: Prepared for on-chain verification

### Architecture

```
+------------------+
| Constitutional   |
|   Framework      |
+--------+---------+
         |
    +----+----+----------------+----------------+
    |         |                |                |
+---v---+ +---v----+    +------v-----+   +------v------+
| Policy| | Audit  |    | Retrieval  |   | Constraint  |
|Registry| Ledger  |    | Engine     |   | Generator   |
+---+---+ +---+----+    +------+-----+   +------+------+
    |         |                |                |
    +----+----+----------------+----------------+
         |
+--------v--------+
| Blockchain      |
| Integration     |
+-----------------+
```

---

## Constitutional Hash

The constitutional hash `cdd01ef066bc6cf2` is the cryptographic anchor for all governance operations.

### Purpose

- **Identity**: Uniquely identifies this constitutional framework
- **Integrity**: Ensures operations are under constitutional governance
- **Audit**: Links all actions to the constitutional authority
- **Compliance**: Validates operations against constitutional requirements

### Usage

Every component in ACGS-2 must reference the constitutional hash:

```python
from enhanced_agent_bus import CONSTITUTIONAL_HASH

# Verify hash in operations
def validate_operation(operation: dict) -> bool:
    if operation.get("constitutional_hash") != CONSTITUTIONAL_HASH:
        raise ConstitutionalViolationError(
            f"Invalid constitutional hash: {operation.get('constitutional_hash')}"
        )
    return True
```

### File Headers

All Python files should include the constitutional hash in their docstring:

```python
"""
Service Name - Description

Constitutional Hash: cdd01ef066bc6cf2
"""
```

### Verification

```python
from enhanced_agent_bus.validators import validate_constitutional_hash

result = validate_constitutional_hash(hash_value)
if not result.is_valid:
    print(f"Constitutional violation: {result.errors}")
```

---

## Policy Registry

The Policy Registry manages constitutional policies with full version control and cryptographic signatures.

### Core Concepts

#### Policy

A policy defines rules, constraints, and governance requirements:

```python
@dataclass
class Policy:
    policy_id: str           # Unique identifier
    name: str                # Human-readable name
    description: str         # Policy description
    status: PolicyStatus     # draft, active, retired
    format: str              # json, yaml
    created_at: datetime
    updated_at: datetime
```

#### Policy Version

Policies are versioned for auditability:

```python
@dataclass
class PolicyVersion:
    version_id: str          # Version identifier
    policy_id: str           # Parent policy
    version: str             # Semantic version (1.0.0)
    content: Dict[str, Any]  # Policy content
    content_hash: str        # SHA-256 of content
    status: VersionStatus    # draft, active, retired
    ab_test_group: Optional[ABTestGroup]  # A/B testing
```

### Creating Policies

```python
from services.policy_registry.app.services import PolicyService

policy_service = PolicyService(crypto_service, cache_service, notification_service)

# Create policy
policy = await policy_service.create_policy(
    name="data-protection-policy",
    content={
        "rules": [
            {"id": "r1", "type": "required", "field": "encryption"},
            {"id": "r2", "type": "required", "field": "access_logging"}
        ],
        "constraints": [
            {"id": "c1", "type": "max_retention", "value": "90_days"}
        ]
    },
    format="json",
    description="Data protection compliance policy"
)

print(f"Created policy: {policy.policy_id}")
```

### Managing Versions

```python
# Create new version with signature
policy_version = await policy_service.create_policy_version(
    policy_id=policy.policy_id,
    content={
        "rules": [
            {"id": "r1", "type": "required", "field": "encryption"},
            {"id": "r2", "type": "required", "field": "access_logging"},
            {"id": "r3", "type": "recommended", "field": "anonymization"}
        ]
    },
    version="1.1.0",
    private_key_b64=private_key,
    public_key_b64=public_key,
    ab_test_group=ABTestGroup.A  # Optional A/B testing
)

# Activate the version
await policy_service.activate_version(policy.policy_id, "1.1.0")
```

### A/B Testing Policies

```python
# Get policy for client (with A/B routing)
content = await policy_service.get_policy_for_client(
    policy_id="pol-abc-123",
    client_id="client-xyz"  # Used for A/B routing
)
```

---

## Cryptographic Signatures

All policy versions are cryptographically signed for integrity verification.

### Signature Creation

```python
from services.policy_registry.app.services import CryptoService

crypto = CryptoService()

# Create signature
signature = crypto.create_policy_signature(
    policy_id="pol-abc-123",
    version="1.0.0",
    content={"rules": [...]},
    private_key_b64=private_key,
    public_key_b64=public_key
)

print(f"Signature: {signature.signature}")
print(f"Key fingerprint: {signature.key_fingerprint}")
```

### Signature Verification

```python
# Verify policy signature
is_valid = await policy_service.verify_policy_signature(
    policy_id="pol-abc-123",
    version="1.0.0"
)

if not is_valid:
    raise SignatureVerificationError("Policy signature invalid!")
```

### Key Management

```python
# Generate key pair
import base64
from cryptography.hazmat.primitives.asymmetric import ed25519

private_key = ed25519.Ed25519PrivateKey.generate()
public_key = private_key.public_key()

private_key_b64 = base64.b64encode(
    private_key.private_bytes_raw()
).decode()
public_key_b64 = base64.b64encode(
    public_key.public_bytes_raw()
).decode()
```

---

## Audit Ledger

The Audit Ledger provides an immutable record of all validation results and governance decisions.

### Core Concepts

#### Validation Result

```python
@dataclass
class ValidationResult:
    is_valid: bool                    # Validation passed
    errors: List[str]                 # Error messages
    warnings: List[str]               # Warning messages
    metadata: Dict[str, Any]          # Additional context
    constitutional_hash: str = "cdd01ef066bc6cf2"
```

#### Audit Entry

```python
@dataclass
class AuditEntry:
    validation_result: ValidationResult
    hash: str                         # SHA-256 of entry
    timestamp: float                  # Unix timestamp
    batch_id: Optional[str]           # Batch identifier
    merkle_proof: Optional[List]      # Proof for verification
```

### Using the Audit Ledger

```python
from services.audit_service.core import AuditLedger, ValidationResult

ledger = AuditLedger(batch_size=100)

# Add validation result
validation = ValidationResult(
    is_valid=True,
    errors=[],
    warnings=["Minor formatting issue"],
    metadata={
        "policy_id": "pol-abc-123",
        "agent_id": "agent-001",
        "action": "validate_code"
    }
)

entry_hash = ledger.add_validation_result(validation)
print(f"Entry hash: {entry_hash}")
```

### Batch Processing

Entries are automatically batched for Merkle tree creation:

```python
# Configure batch size
ledger = AuditLedger(batch_size=100)

# Add entries (batched automatically)
for result in validation_results:
    ledger.add_validation_result(result)

# Force commit current batch
root_hash = ledger.force_commit_batch()
print(f"Batch root hash: {root_hash}")
```

### Ledger Statistics

```python
stats = ledger.get_ledger_stats()
print(f"""
Ledger Statistics:
- Total entries: {stats['total_entries']}
- Current batch size: {stats['current_batch_size']}
- Batches committed: {stats['batches_committed']}
- Current root hash: {stats['current_root_hash']}
""")
```

---

## Merkle Tree Verification

Merkle trees provide efficient verification of audit entries.

### How It Works

```
                    Root Hash
                   /         \
            Hash(L+R)      Hash(L+R)
           /      \        /      \
       Entry1   Entry2  Entry3  Entry4
```

### Verifying Entries

```python
# Get entry with proof
entry = ledger.entries[0]

# Verify using proof
is_valid = ledger.verify_entry(
    entry_hash=entry.hash,
    merkle_proof=entry.merkle_proof,
    root_hash=ledger.merkle_tree.get_root_hash()
)

if is_valid:
    print("Entry verified successfully!")
```

### Batch Verification

```python
# Get entries for a batch
batch_entries = ledger.get_entries_by_batch("batch_0_1705312200")

# All entries can be verified against the batch root
root_hash = ledger.get_batch_root_hash("batch_0_1705312200")

for entry in batch_entries:
    verified = ledger.verify_entry(
        entry_hash=entry.hash,
        merkle_proof=entry.merkle_proof,
        root_hash=root_hash
    )
    print(f"Entry {entry.hash[:16]}... verified: {verified}")
```

---

## Blockchain Integration

The Audit Ledger prepares transactions for blockchain anchoring.

### Preparing Transactions

```python
# Prepare blockchain transaction data
tx_data = ledger.prepare_blockchain_transaction("batch_0_1705312200")

print(f"""
Blockchain Transaction:
- Batch ID: {tx_data['batch_id']}
- Root Hash: {tx_data['root_hash']}
- Entry Count: {tx_data['entry_count']}
- Timestamp: {tx_data['timestamp']}
""")
```

### Supported Blockchains

The system supports multiple blockchain backends:

#### Hyperledger Fabric

```python
from services.audit_service.blockchain.hyperledger_fabric import FabricClient

fabric = FabricClient(
    network_config="network-config.yaml",
    channel="governance-channel"
)

# Submit batch root
tx_id = await fabric.submit_root_hash(
    batch_id=tx_data['batch_id'],
    root_hash=tx_data['root_hash']
)
```

#### Ethereum L2

```python
from services.audit_service.blockchain.ethereum_l2 import EthereumClient

eth = EthereumClient(
    rpc_url="https://l2-rpc.example.com",
    contract_address="0x..."
)

# Anchor to L2
tx_hash = await eth.anchor_root(
    root_hash=tx_data['root_hash'],
    metadata={"batch_id": tx_data['batch_id']}
)
```

#### Arweave (Permanent Storage)

```python
from services.audit_service.blockchain.arweave import ArweaveClient

arweave = ArweaveClient(wallet_path="wallet.json")

# Store full batch data
tx_id = await arweave.store_batch(
    batch_data=tx_data,
    tags={"app": "acgs2", "type": "audit_batch"}
)
```

---

## Constitutional Retrieval System

RAG-based retrieval for constitutional precedents and documents.

### Indexing Documents

```python
from services.core.constitutional_retrieval_system import (
    RetrievalEngine,
    VectorDatabaseManager,
    DocumentProcessor
)

# Initialize components
vector_db = VectorDatabaseManager()
doc_processor = DocumentProcessor()
engine = RetrievalEngine(vector_db, doc_processor)

# Initialize collections
await engine.initialize_collections()

# Index documents
documents = [
    {
        "content": "The right to privacy shall be respected...",
        "metadata": {
            "doc_type": "constitution",
            "chapter": "Fundamental Rights",
            "article": "Article 21"
        }
    },
    {
        "content": "In the case of Smith v. Corporation...",
        "metadata": {
            "doc_type": "precedent",
            "court": "Supreme Court",
            "date": "2023-05-15",
            "legal_domain": "privacy"
        }
    }
]

await engine.index_documents(documents)
```

### Retrieving Similar Documents

```python
results = await engine.retrieve_similar_documents(
    query="privacy rights in digital communications",
    limit=5,
    filters={"doc_type": "constitution"}
)

for result in results:
    print(f"Score: {result['relevance_score']:.3f}")
    print(f"Content: {result['payload']['content'][:200]}...")
```

### Retrieving Precedents

```python
precedents = await engine.retrieve_precedents_for_case(
    case_description="User data was collected without consent...",
    legal_domain="privacy",
    limit=10
)

for p in precedents:
    print(f"Relevance: {p['precedent_relevance']:.3f}")
    print(f"Court: {p['payload'].get('court')}")
    print(f"Summary: {p['payload']['content'][:200]}...")
```

### Hybrid Search

Combines semantic and keyword-based retrieval:

```python
results = await engine.hybrid_search(
    query="data protection compliance requirements",
    keyword_filters=["GDPR", "consent", "breach"],
    semantic_weight=0.7,
    keyword_weight=0.3,
    limit=10
)

for r in results:
    print(f"Hybrid score: {r['hybrid_score']:.3f}")
```

---

## Multi-Agent Deliberation

High-risk decisions undergo multi-agent review.

### Deliberation Process

```
Message → Impact Assessment → Threshold Check
                                    |
                        +-----------+-----------+
                        |                       |
                   Low Risk                High Risk
                        |                       |
                   Fast Lane              Deliberation
                        |                       |
                   Process              Multi-Agent Vote
                                              |
                                    Human Review (if needed)
                                              |
                                       Decision
```

### Impact Assessment

```python
from enhanced_agent_bus.deliberation_layer import (
    calculate_message_impact,
    get_adaptive_router
)

# Calculate impact score
score = calculate_message_impact({
    "action": "delete_user_data",
    "user_count": 10000,
    "irreversible": True
})

print(f"Impact score: {score:.3f}")  # High score for this action
```

### Routing Configuration

```python
from enhanced_agent_bus.deliberation_layer import AdaptiveRouter

router = AdaptiveRouter(
    impact_threshold=0.8,        # Scores >= 0.8 go to deliberation
    deliberation_timeout=300,    # 5 minute timeout
    enable_learning=True         # Adaptive threshold adjustment
)

# Route a message
decision = await router.route_message(message)

if decision['lane'] == 'deliberation':
    print(f"Queued for review: {decision['item_id']}")
    print(f"Estimated wait: {decision['estimated_wait_time']}s")
```

### Deliberation Queue

```python
from enhanced_agent_bus.deliberation_layer import get_deliberation_queue

queue = get_deliberation_queue()

# Enqueue for deliberation
item_id = await queue.enqueue_for_deliberation(
    message=message,
    requires_human_review=True,
    requires_multi_agent_vote=True,
    timeout_seconds=600
)

# Check status
status = await queue.get_item_status(item_id)
print(f"Deliberation status: {status}")
```

### LLM-Assisted Decision Support

```python
from enhanced_agent_bus.deliberation_layer import get_llm_assistant

assistant = get_llm_assistant()

# Get AI analysis
analysis = await assistant.analyze_decision(
    message=message,
    context={
        "relevant_policies": ["pol-abc-123"],
        "precedents": precedents,
        "risk_factors": ["data_loss", "compliance"]
    }
)

print(f"Recommendation: {analysis['recommendation']}")
print(f"Confidence: {analysis['confidence']:.2f}")
print(f"Reasoning: {analysis['reasoning']}")
```

---

## Constraint Generation

Automatic generation of constraints from policies.

### Using the Constraint Generator

```python
from services.core.constraint_generation_system import ConstraintGenerator

generator = ConstraintGenerator()

# Generate constraints from policy
constraints = generator.generate_constraints(
    policy_content={
        "rules": [
            {"id": "r1", "type": "required", "field": "encryption", "algorithm": "AES-256"},
            {"id": "r2", "type": "required", "field": "audit_logging"}
        ]
    }
)

for constraint in constraints:
    print(f"Constraint: {constraint['id']}")
    print(f"  Type: {constraint['type']}")
    print(f"  Rule: {constraint['rule']}")
```

### Language-Specific Constraints

```python
from services.core.constraint_generation_system import LanguageConstraints

lang_constraints = LanguageConstraints()

# Get Python-specific constraints
python_rules = lang_constraints.get_language_rules("python")

for rule in python_rules:
    print(f"Rule: {rule['name']}")
    print(f"  Pattern: {rule['pattern']}")
    print(f"  Severity: {rule['severity']}")
```

### Quality Scoring

```python
from services.core.constraint_generation_system import QualityScorer

scorer = QualityScorer()

# Score constraint quality
score = scorer.score_constraints(constraints)

print(f"Quality score: {score['overall']:.2f}")
print(f"Coverage: {score['coverage']:.2%}")
print(f"Specificity: {score['specificity']:.2f}")
```

---

## Compliance Validation

### Validating Operations

```python
from enhanced_agent_bus.validators import (
    ValidationResult,
    validate_constitutional_hash,
    validate_message_content
)

def validate_operation(operation: dict) -> ValidationResult:
    result = ValidationResult()

    # Check constitutional hash
    hash_result = validate_constitutional_hash(
        operation.get("constitutional_hash", "")
    )
    result.merge(hash_result)

    # Check content
    content_result = validate_message_content(operation.get("content", {}))
    result.merge(content_result)

    # Add custom validation
    if operation.get("risk_level") == "high":
        if not operation.get("approval_id"):
            result.add_error("High-risk operations require approval")

    return result
```

### Compliance Reports

```python
from services.integration.search_platform import ConstitutionalCodeSearchService

async def generate_compliance_report(paths: list) -> dict:
    async with ConstitutionalCodeSearchService() as service:
        # Verify constitutional hashes
        hash_result = await service.verify_constitutional_hash(paths)

        # Scan for violations
        violation_result = await service.scan_for_violations(paths)

        # Find security issues
        security_result = await service.find_security_issues(paths)

        return {
            "hash_compliance": {
                "compliant_files": len(hash_result.compliant_matches),
                "non_compliant_files": len(hash_result.violations)
            },
            "code_violations": {
                "total": len(violation_result.violations),
                "critical": len([v for v in violation_result.violations if v.severity == "critical"]),
                "high": len([v for v in violation_result.violations if v.severity == "high"])
            },
            "security_issues": {
                "total": len(security_result.violations),
                "critical": len(security_result.critical_violations)
            }
        }
```

---

## Best Practices

### 1. Always Validate Constitutional Hash

```python
# Start of every operation
if operation.constitutional_hash != CONSTITUTIONAL_HASH:
    raise ConstitutionalViolationError()
```

### 2. Sign All Policy Changes

```python
# Never create unsigned versions
policy_version = await policy_service.create_policy_version(
    ...,
    private_key_b64=private_key,  # Required
    public_key_b64=public_key     # Required
)
```

### 3. Audit All Decisions

```python
# Log every validation result
result = validate_operation(operation)
entry_hash = audit_ledger.add_validation_result(result)
```

### 4. Use Appropriate Impact Thresholds

```python
# Lower threshold for sensitive operations
router = AdaptiveRouter(
    impact_threshold=0.6  # More conservative
)
```

### 5. Regular Compliance Scans

```python
# Schedule regular scans
@scheduler.cron("0 2 * * *")  # Daily at 2 AM
async def daily_compliance_scan():
    report = await generate_compliance_report(["src/", "services/"])
    if report["security_issues"]["critical"] > 0:
        await send_alert("Critical security issues found!")
```

### 6. Version Control Policies

```python
# Always use semantic versioning
await policy_service.create_policy_version(
    version="1.2.3",  # Major.Minor.Patch
    ...
)
```

### 7. Blockchain Anchoring for Critical Batches

```python
# Anchor important audit batches
if batch.contains_critical_decisions:
    tx_data = ledger.prepare_blockchain_transaction(batch.id)
    await blockchain.anchor_root(tx_data['root_hash'])
```

---

## Next Steps

- [Enhanced Agent Bus Guide](./enhanced-agent-bus.md) - Messaging infrastructure
- [Search Platform Guide](./search-platform.md) - Search capabilities
- [API Reference](./api-reference.md) - Complete API documentation
