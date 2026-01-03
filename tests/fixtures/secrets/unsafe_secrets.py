"""
ACGS-2 Unsafe Secrets Test Fixtures
Constitutional Hash: cdd01ef066bc6cf2

This file contains REALISTIC-LOOKING FAKE secrets that should FAIL detection.
These are randomly generated test values that match real credential patterns.

⚠️ CRITICAL: ALL SECRETS HERE ARE FAKE! RANDOMLY GENERATED FOR TESTING ONLY!
⚠️ DO NOT USE THESE VALUES ANYWHERE! THEY ARE FOR VALIDATION TESTING ONLY!

These values should trigger secrets detection to ensure the system works correctly.
"""

# =============================================================================
# ❌ UNSAFE: CLAUDE_CODE_OAUTH_TOKEN Pattern
# =============================================================================
# Pattern: ^sk-ant-oat\d{2}-[A-Za-z0-9_-]{60,}$
# These should FAIL detection (fake but realistic-looking)

CLAUDE_CODE_OAUTH_TOKEN_FAKE_1 = (
    "sk-ant-oat01-RealLookingButFakePleaseDontUseThisToken123456789012345678901234567890ABC"
)
CLAUDE_CODE_OAUTH_TOKEN_FAKE_2 = (
    "sk-ant-oat99-AnotherFakeTokenThatLooksLikeItCouldBeRealButIsntTrustMeXYZ1234567890"
)


# =============================================================================
# ❌ UNSAFE: OPENAI_API_KEY Pattern
# =============================================================================
# Pattern: ^sk-[A-Za-z0-9]{20,}$
# These should FAIL detection (fake but realistic-looking)

OPENAI_API_KEY_FAKE_1 = "sk-FakeButValidFormatOpenAIKey123456789012345"
OPENAI_API_KEY_FAKE_2 = "sk-AnotherFakeLookingKey987654321ABCDEF"
OPENAI_API_KEY_FAKE_3 = "sk-proj-1234567890ABCDEFGHIJKLMNOPabcdefghijklmnop"


# =============================================================================
# ❌ UNSAFE: OPENROUTER_API_KEY Pattern
# =============================================================================
# Pattern: ^sk-or-v1-[A-Za-z0-9]{60,}$
# These should FAIL detection (fake but realistic-looking)

OPENROUTER_API_KEY_FAKE_1 = (
    "sk-or-v1-FakeLookingOpenRouterKeyThatMatchesPatternExactly123456789012345678901234567890"
)
OPENROUTER_API_KEY_FAKE_2 = (
    "sk-or-v1-AnotherFakeTokenForTestingPurposesOnlyDoNotUse987654321ABCDEFabcdef"
)


# =============================================================================
# ❌ UNSAFE: HF_TOKEN (HuggingFace) Pattern
# =============================================================================
# Pattern: ^hf_[A-Za-z0-9]{30,}$
# These should FAIL detection (fake but realistic-looking)

HF_TOKEN_FAKE_1 = "hf_FakeLookingHuggingFaceTokenForTestingOnly123456789012345678"
HF_TOKEN_FAKE_2 = "hf_AnotherFakeTokenThatLooksRealistic987654321ABCDEFGHIJKLMabcdefgh"


# =============================================================================
# ❌ UNSAFE: ANTHROPIC_API_KEY Pattern
# =============================================================================
# Pattern: ^sk-ant-[A-Za-z0-9_-]{80,}$
# These should FAIL detection (fake but realistic-looking)

ANTHROPIC_API_KEY_FAKE_1 = "sk-ant-FakeAnthropicKeyForTestingPurposesOnlyDoNotUseInProductionOrDevelopment1234567890ABCDEFGHIJKLMNOP"
ANTHROPIC_API_KEY_FAKE_2 = "sk-ant-AnotherFakeLookingAnthropicKeyThatMatchesThePatternButIsCompletelyRandomData987654321XYZabcdefgh"


# =============================================================================
# ❌ UNSAFE: AWS_ACCESS_KEY_ID Pattern
# =============================================================================
# Pattern: ^AKIA[A-Z0-9]{16}$
# These should FAIL detection (fake but realistic-looking)

AWS_ACCESS_KEY_ID_FAKE_1 = "AKIAFAKE1234567890AB"
AWS_ACCESS_KEY_ID_FAKE_2 = "AKIATEST9876543210XY"
AWS_ACCESS_KEY_ID_FAKE_3 = "AKIARANDOMFAKEKEY123"


# =============================================================================
# ❌ UNSAFE: JWT_SECRET Pattern
# =============================================================================
# Pattern: ^[A-Fa-f0-9]{64}$
# These should FAIL detection (fake but realistic-looking hex strings)

JWT_SECRET_FAKE_1 = "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
JWT_SECRET_FAKE_2 = "FEDCBA0987654321FEDCBA0987654321FEDCBA0987654321FEDCBA0987654321"
JWT_SECRET_FAKE_3 = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"


# =============================================================================
# ❌ UNSAFE: VAULT_TOKEN Pattern
# =============================================================================
# Pattern: ^(hvs\.|s\.)[A-Za-z0-9]{20,}$
# These should FAIL detection (fake but realistic-looking)

VAULT_TOKEN_FAKE_1 = "hvs.FakeVaultTokenForTestingOnly123456789012345"
VAULT_TOKEN_FAKE_2 = "s.AnotherFakeVaultTokenThatLooksRealButIsnt987654321"
VAULT_TOKEN_FAKE_3 = "hvs.RandomlyGeneratedFakeVaultTokenABCDEF"


# =============================================================================
# ❌ UNSAFE: Configuration Dictionary with Fake Secrets
# =============================================================================

UNSAFE_CONFIG = {
    "ai_providers": {
        "claude_code": "sk-ant-oat01-FakeTokenForTestingOnlyDoNotUse123456789012345678901234567890",
        "openai": "sk-FakeOpenAIKey123456789012345678",
        "openrouter": "sk-or-v1-FakeOpenRouterKey1234567890123456789012345678901234567890",
        "huggingface": "hf_FakeHFToken123456789012345678901234567890",
        "anthropic": "sk-ant-FakeAnthropicKey1234567890123456789012345678901234567890123456789012345678901234567890",
    },
    "infrastructure": {
        "aws_access_key_id": "AKIAFAKE1234567890AB",
        "aws_secret_access_key": "FakeAWSSecretKey1234567890/ABCDEF",
        "jwt_secret": "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        "vault_token": "hvs.FakeVaultToken123456789012345",
    },
}


# =============================================================================
# ❌ UNSAFE: Class-based Configuration with Fake Secrets
# =============================================================================


class UnsafeSecretsConfig:
    """Unsafe configuration with realistic-looking fake secrets."""

    # AI Provider Keys (ALL FAKE - FOR TESTING ONLY)
    CLAUDE_CODE_OAUTH_TOKEN = "sk-ant-oat01-FakeClaudeCodeToken123456789012345678901234567890ABCDEF"
    OPENAI_API_KEY = "sk-FakeOpenAIKey987654321ABCDEFGH"
    OPENROUTER_API_KEY = "sk-or-v1-FakeOpenRouterKey1234567890123456789012345678901234567890"
    HF_TOKEN = "hf_FakeHuggingFaceToken123456789012345678901234"
    ANTHROPIC_API_KEY = (
        "sk-ant-FakeAnthropicKey123456789012345678901234567890123456789012345678901234567890"
    )

    # Infrastructure Secrets (ALL FAKE - FOR TESTING ONLY)
    AWS_ACCESS_KEY_ID = "AKIAFAKE1234567890AB"
    AWS_SECRET_ACCESS_KEY = "FakeAWSSecretKey/1234567890ABCDEF"
    JWT_SECRET = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    VAULT_TOKEN = "hvs.FakeVaultToken123456789012345"


# =============================================================================
# ❌ UNSAFE: Environment-style Assignments with Fake Secrets
# =============================================================================

os_environ_unsafe = {
    "CLAUDE_CODE_OAUTH_TOKEN": "sk-ant-oat99-FakeTokenDoNotUse123456789012345678901234567890ABCDEFGHIJ",
    "OPENAI_API_KEY": "sk-FakeKey123456789012345678",
    "OPENROUTER_API_KEY": "sk-or-v1-FakeRouterKey1234567890123456789012345678901234567890",
    "HF_TOKEN": "hf_FakeToken123456789012345678901234567890",
    "ANTHROPIC_API_KEY": "sk-ant-FakeAntKey1234567890123456789012345678901234567890123456789012345678901234",
    "AWS_ACCESS_KEY_ID": "AKIATEST9876543210XY",
    "JWT_SECRET": "fedcba0987654321fedcba0987654321fedcba0987654321fedcba0987654321",
    "VAULT_TOKEN": "s.FakeVaultToken987654321ABCDEF",
}


# =============================================================================
# ❌ UNSAFE: Multi-line Configuration with Fake Secrets
# =============================================================================

UNSAFE_MULTILINE_CONFIG = """
# FAKE SECRETS FOR TESTING - DO NOT USE!
CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-FakeToken123456789012345678901234567890ABCDEFGHIJKLMNOP
OPENAI_API_KEY=sk-FakeOpenAI123456789012345678
OPENROUTER_API_KEY=sk-or-v1-FakeRouter1234567890123456789012345678901234567890
HF_TOKEN=hf_FakeHF123456789012345678901234567890
ANTHROPIC_API_KEY=sk-ant-FakeAnt1234567890123456789012345678901234567890123456789012345678901234
AWS_ACCESS_KEY_ID=AKIAFAKE1234567890AB
JWT_SECRET=abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890
VAULT_TOKEN=hvs.FakeVault123456789012345
"""

UNSAFE_JSON_CONFIG = """
{
    "claude_code_token": "sk-ant-oat01-FakeJSON123456789012345678901234567890ABCDEFGHIJKLMNOP",
    "openai_key": "sk-FakeJSONOpenAI123456789012345",
    "openrouter_key": "sk-or-v1-FakeJSONRouter1234567890123456789012345678901234567890",
    "hf_token": "hf_FakeJSONHF123456789012345678901234567890",
    "anthropic_key": "sk-ant-FakeJSONAnt123456789012345678901234567890123456789012345678901234567890",
    "aws_access_key_id": "AKIAJSONFAKE12345678",
    "jwt_secret": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
    "vault_token": "hvs.FakeJSONVault123456789012345"
}
"""


# =============================================================================
# ❌ UNSAFE: Function Return Values with Fake Secrets
# =============================================================================


def get_unsafe_api_key():
    """Return a fake but realistic-looking API key for testing."""
    return "sk-FakeFunction123456789012345"


def get_unsafe_token():
    """Return a fake but realistic-looking token for testing."""
    return "sk-ant-oat01-FakeFunctionToken123456789012345678901234567890ABCDEFGH"


def get_unsafe_aws_key():
    """Return a fake but realistic-looking AWS key for testing."""
    return "AKIAFUNC1234567890AB"


def get_unsafe_jwt_secret():
    """Return a fake but realistic-looking JWT secret for testing."""
    return "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"


# =============================================================================
# ❌ UNSAFE: Assignment Variations
# =============================================================================

# Direct assignment
api_key = "sk-FakeAssignment123456789012345"

# Dictionary value
config = {"key": "sk-ant-oat01-FakeDictValue123456789012345678901234567890ABCDEFG"}

# List element
keys = ["sk-FakeList123456789012345678"]

# Tuple element
credentials = ("AKIATUPL1234567890AB", "FakeSecretKey123")

# F-string (still detectable)
formatted_key = "sk-FakeFormatted123456789012345"

# Concatenation (might be detectable depending on scanning)
partial1 = "sk-ant-oat01-"
partial2 = "FakeConcat123456789012345678901234567890ABCDEFGHIJKLMNOP"
concatenated_key = partial1 + partial2  # This becomes a real-looking key


# =============================================================================
# ❌ UNSAFE: Edge Cases That Should Still Detect
# =============================================================================

# Inline in data structure
INLINE_CONFIG = {
    "providers": [
        {"name": "openai", "key": "sk-FakeInline123456789012345"},
        {
            "name": "anthropic",
            "key": "sk-ant-FakeInlineAnt123456789012345678901234567890123456789012345678901234",
        },
    ]
}

# In SQL-like string
SQL_QUERY = "INSERT INTO secrets (api_key) VALUES ('sk-FakeSQL123456789012345678')"

# In URL
API_URL = "https://api.example.com/v1/chat?api_key=sk-FakeURL123456789012345678"

# In JSON string
JSON_PAYLOAD = '{"api_key": "sk-FakeJSONPayload123456789012345"}'

# In base64 (might not be caught, but included for completeness)
# Note: Base64 detection would require additional entropy/pattern analysis
BASE64_EXAMPLE = (
    "c2stRmFrZUJhc2U2NEtleTEyMzQ1Njc4OTAxMjM0NQ=="  # sk-FakeBase64Key12345678901234 encoded
)


# =============================================================================
# IMPORTANT REMINDER
# =============================================================================
# ⚠️ ALL VALUES IN THIS FILE ARE FAKE AND RANDOMLY GENERATED ⚠️
# ⚠️ NEVER USE THESE IN PRODUCTION OR DEVELOPMENT ⚠️
# ⚠️ THESE ARE FOR SECRETS DETECTION TESTING ONLY ⚠️
