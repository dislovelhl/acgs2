"""
ACGS-2 Unified Configuration System
Constitutional Hash: cdd01ef066bc6cf2

Uses pydantic-settings for type-safe environment configuration.
"""

import os
from functools import lru_cache
from typing import List, Optional

from pydantic import Field, SecretStr, field_validator, model_validator

try:
    from src.core.shared.types import JSONDict
except ImportError:
    from typing import Any, Dict

    JSONDict = Dict[str, Any]

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict

    HAS_PYDANTIC_SETTINGS = True
except ImportError:
    HAS_PYDANTIC_SETTINGS = False
    from pydantic import BaseModel as BaseSettings

    class SettingsConfigDict(dict):
        pass


if HAS_PYDANTIC_SETTINGS:

    class RedisSettings(BaseSettings):
        """Redis connection settings."""

        url: str = Field("redis://localhost:6379", validation_alias="REDIS_URL")
        host: str = Field("localhost", validation_alias="REDIS_HOST")
        port: int = Field(6379, validation_alias="REDIS_PORT")
        db: int = Field(0, validation_alias="REDIS_DB")
        max_connections: int = Field(100, validation_alias="REDIS_MAX_CONNECTIONS")
        socket_timeout: float = Field(5.0, validation_alias="REDIS_SOCKET_TIMEOUT")
        retry_on_timeout: bool = Field(True, validation_alias="REDIS_RETRY_ON_TIMEOUT")
        ssl: bool = Field(False, validation_alias="REDIS_SSL")
        ssl_cert_reqs: str = Field(
            "none", validation_alias="REDIS_SSL_CERT_REQS"
        )  # none, optional, required
        ssl_ca_certs: Optional[str] = Field(None, validation_alias="REDIS_SSL_CA_CERTS")
        socket_keepalive: bool = Field(True, validation_alias="REDIS_SOCKET_KEEPALIVE")
        health_check_interval: int = Field(30, validation_alias="REDIS_HEALTH_CHECK_INTERVAL")

    class AISettings(BaseSettings):
        """AI Service settings."""

        openrouter_api_key: Optional[SecretStr] = Field(None, validation_alias="OPENROUTER_API_KEY")
        hf_token: Optional[SecretStr] = Field(None, validation_alias="HF_TOKEN")
        openai_api_key: Optional[SecretStr] = Field(None, validation_alias="OPENAI_API_KEY")
        constitutional_hash: str = Field("cdd01ef066bc6cf2", validation_alias="CONSTITUTIONAL_HASH")

    class BlockchainSettings(BaseSettings):
        """Blockchain integration settings."""

        eth_l2_network: str = Field("optimism", validation_alias="ETH_L2_NETWORK")
        eth_rpc_url: str = Field("https://mainnet.optimism.io", validation_alias="ETH_RPC_URL")
        contract_address: Optional[str] = Field(None, validation_alias="AUDIT_CONTRACT_ADDRESS")
        private_key: Optional[SecretStr] = Field(None, validation_alias="BLOCKCHAIN_PRIVATE_KEY")

    class SecuritySettings(BaseSettings):
        """Security and Auth settings."""

        api_key_internal: Optional[SecretStr] = Field(None, validation_alias="API_KEY_INTERNAL")
        cors_origins: List[str] = Field(["*"], validation_alias="CORS_ORIGINS")
        jwt_secret: Optional[SecretStr] = Field(None, validation_alias="JWT_SECRET")
        jwt_public_key: str = Field(
            "SYSTEM_PUBLIC_KEY_PLACEHOLDER", validation_alias="JWT_PUBLIC_KEY"
        )
        admin_api_key: Optional[SecretStr] = Field(None, validation_alias="ADMIN_API_KEY")

        @field_validator("jwt_secret", "api_key_internal")
        @classmethod
        def check_no_placeholders(cls, v: Optional[SecretStr]) -> Optional[SecretStr]:
            """Ensure sensitive keys don't use weak placeholders."""
            if v is not None:
                secret_val = v.get_secret_value()
                if secret_val in ["PLACEHOLDER", "CHANGE_ME", "DANGEROUS_DEFAULT", "dev-secret"]:
                    raise ValueError("Sensitive credential uses a forbidden placeholder value")

                # Check secret strength if it's a JWT secret
                # Note: We can't easily distinguish which field 'v' is here without 'info',
                # but applying it to both is safe as both should be strong.
                if len(secret_val) < 32:
                    # We check the environment in the model_validator below for the hard stop,
                    # but we can log a warning here or raise if we want to be very strict.
                    pass
            return v

        @field_validator("cors_origins")
        @classmethod
        def validate_cors_origins(cls, v: List[str], info) -> List[str]:
            """Block wildcard CORS in production environments."""
            # Get the environment from the parent Settings object if available
            # During validation, we need to check the ENV variable directly
            env = os.getenv("APP_ENV", "development").lower()

            if env == "production" and "*" in v:
                raise ValueError(
                    "SECURITY ERROR: Wildcard CORS origins (*) are not allowed in production. "
                    "Please set CORS_ORIGINS to explicit domain allowlist."
                )
            return v

    class OPASettings(BaseSettings):
        """OPA (Open Policy Agent) settings."""

        url: str = Field("http://localhost:8181", validation_alias="OPA_URL")
        mode: str = Field("http", validation_alias="OPA_MODE")  # http, embedded, fallback
        # SECURITY FIX (VULN-002): OPA is now ALWAYS fail-closed.
        # Parameter removed to prevent insecure overrides.
        fail_closed: bool = True
        ssl_verify: bool = Field(True, validation_alias="OPA_SSL_VERIFY")
        ssl_cert: Optional[str] = Field(None, validation_alias="OPA_SSL_CERT")
        ssl_key: Optional[str] = Field(None, validation_alias="OPA_SSL_KEY")

    class AuditSettings(BaseSettings):
        """Audit Service settings."""

        url: str = Field("http://localhost:8001", validation_alias="AUDIT_SERVICE_URL")

    class BundleSettings(BaseSettings):
        """Policy Bundle settings."""

        registry_url: str = Field("http://localhost:5000", validation_alias="BUNDLE_REGISTRY_URL")
        storage_path: str = Field("./storage/bundles", validation_alias="BUNDLE_STORAGE_PATH")
        s3_bucket: Optional[str] = Field(None, validation_alias="BUNDLE_S3_BUCKET")
        github_webhook_secret: Optional[SecretStr] = Field(
            None, validation_alias="GITHUB_WEBHOOK_SECRET"
        )

    class ServiceSettings(BaseSettings):
        """Service URL settings for inter-service communication."""

        agent_bus_url: str = Field("http://localhost:8000", validation_alias="AGENT_BUS_URL")
        policy_registry_url: str = Field(
            "http://localhost:8000", validation_alias="POLICY_REGISTRY_URL"
        )
        api_gateway_url: str = Field("http://localhost:8080", validation_alias="API_GATEWAY_URL")
        tenant_management_url: str = Field(
            "http://localhost:8500", validation_alias="TENANT_MANAGEMENT_URL"
        )
        hitl_approvals_url: str = Field(
            "http://localhost:8200", validation_alias="HITL_APPROVALS_URL"
        )
        ml_governance_url: str = Field(
            "http://localhost:8400", validation_alias="ML_GOVERNANCE_URL"
        )
        compliance_docs_url: str = Field(
            "http://localhost:8100", validation_alias="COMPLIANCE_DOCS_URL"
        )
        audit_service_url: str = Field(
            "http://localhost:8300", validation_alias="AUDIT_SERVICE_URL"
        )

    class TelemetrySettings(BaseSettings):
        """OpenTelemetry and observability settings."""

        otlp_endpoint: str = Field(
            "http://localhost:4317", validation_alias="OTEL_EXPORTER_OTLP_ENDPOINT"
        )
        service_name: str = Field("acgs2", validation_alias="OTEL_SERVICE_NAME")
        export_traces: bool = Field(True, validation_alias="OTEL_EXPORT_TRACES")
        export_metrics: bool = Field(True, validation_alias="OTEL_EXPORT_METRICS")
        trace_sample_rate: float = Field(1.0, validation_alias="OTEL_TRACE_SAMPLE_RATE")

    class AWSSettings(BaseSettings):
        """AWS/S3 storage settings (supports MinIO for local development)."""

        access_key_id: Optional[SecretStr] = Field(None, validation_alias="AWS_ACCESS_KEY_ID")
        secret_access_key: Optional[SecretStr] = Field(
            None, validation_alias="AWS_SECRET_ACCESS_KEY"
        )
        region: str = Field("us-east-1", validation_alias="AWS_REGION")
        s3_endpoint_url: Optional[str] = Field(None, validation_alias="S3_ENDPOINT_URL")

    class SearchPlatformSettings(BaseSettings):
        """Search Platform integration settings."""

        url: str = Field("http://localhost:9080", validation_alias="SEARCH_PLATFORM_URL")
        timeout_seconds: float = Field(30.0, validation_alias="SEARCH_PLATFORM_TIMEOUT")
        max_connections: int = Field(100, validation_alias="SEARCH_PLATFORM_MAX_CONNECTIONS")
        max_retries: int = Field(3, validation_alias="SEARCH_PLATFORM_MAX_RETRIES")
        retry_delay_seconds: float = Field(1.0, validation_alias="SEARCH_PLATFORM_RETRY_DELAY")
        circuit_breaker_threshold: int = Field(
            5, validation_alias="SEARCH_PLATFORM_CIRCUIT_THRESHOLD"
        )
        circuit_breaker_timeout: float = Field(
            30.0, validation_alias="SEARCH_PLATFORM_CIRCUIT_TIMEOUT"
        )
        enable_compliance: bool = Field(True, validation_alias="SEARCH_PLATFORM_ENABLE_COMPLIANCE")

    class QualitySettings(BaseSettings):
        """Code quality and SonarQube settings."""

        sonarqube_url: str = Field("http://localhost:9000", validation_alias="SONARQUBE_URL")
        sonarqube_token: Optional[SecretStr] = Field(None, validation_alias="SONARQUBE_TOKEN")
        enable_local_analysis: bool = Field(True, validation_alias="QUALITY_ENABLE_LOCAL_ANALYSIS")

    class MACISettings(BaseSettings):
        """MACI (Multi-Agent Constitutional Intelligence) enforcement settings."""

        strict_mode: bool = Field(True, validation_alias="MACI_STRICT_MODE")
        default_role: Optional[str] = Field(None, validation_alias="MACI_DEFAULT_ROLE")
        config_path: Optional[str] = Field(None, validation_alias="MACI_CONFIG_PATH")

    class VaultSettings(BaseSettings):
        """HashiCorp Vault integration settings."""

        address: str = Field("http://127.0.0.1:8200", validation_alias="VAULT_ADDR")
        token: Optional[SecretStr] = Field(None, validation_alias="VAULT_TOKEN")
        namespace: Optional[str] = Field(None, validation_alias="VAULT_NAMESPACE")
        transit_mount: str = Field("transit", validation_alias="VAULT_TRANSIT_MOUNT")
        kv_mount: str = Field("secret", validation_alias="VAULT_KV_MOUNT")
        kv_version: int = Field(2, validation_alias="VAULT_KV_VERSION")
        timeout: float = Field(30.0, validation_alias="VAULT_TIMEOUT")
        verify_tls: bool = Field(True, validation_alias="VAULT_VERIFY_TLS")
        ca_cert: Optional[str] = Field(None, validation_alias="VAULT_CACERT")
        client_cert: Optional[str] = Field(None, validation_alias="VAULT_CLIENT_CERT")
        client_key: Optional[str] = Field(None, validation_alias="VAULT_CLIENT_KEY")

    class VotingSettings(BaseSettings):
        """Voting and deliberation settings for event-driven vote collection."""

        default_timeout_seconds: int = Field(30, validation_alias="VOTING_DEFAULT_TIMEOUT_SECONDS")
        vote_topic_pattern: str = Field(
            "acgs.tenant.{tenant_id}.votes", validation_alias="VOTING_VOTE_TOPIC_PATTERN"
        )
        audit_topic_pattern: str = Field(
            "acgs.tenant.{tenant_id}.audit.votes", validation_alias="VOTING_AUDIT_TOPIC_PATTERN"
        )
        redis_election_prefix: str = Field(
            "election:", validation_alias="VOTING_REDIS_ELECTION_PREFIX"
        )
        enable_weighted_voting: bool = Field(True, validation_alias="VOTING_ENABLE_WEIGHTED")
        signature_algorithm: str = Field(
            "HMAC-SHA256", validation_alias="VOTING_SIGNATURE_ALGORITHM"
        )
        audit_signature_key: Optional[SecretStr] = Field(
            None, validation_alias="AUDIT_SIGNATURE_KEY"
        )
        timeout_check_interval_seconds: int = Field(
            5, validation_alias="VOTING_TIMEOUT_CHECK_INTERVAL"
        )

    class SMTPSettings(BaseSettings):
        """SMTP email delivery settings."""

        host: str = Field("localhost", validation_alias="SMTP_HOST")
        port: int = Field(587, validation_alias="SMTP_PORT")
        username: Optional[str] = Field(None, validation_alias="SMTP_USERNAME")
        password: Optional[SecretStr] = Field(None, validation_alias="SMTP_PASSWORD")
        use_tls: bool = Field(True, validation_alias="SMTP_USE_TLS")
        use_ssl: bool = Field(False, validation_alias="SMTP_USE_SSL")
        from_email: str = Field("noreply@acgs2.local", validation_alias="SMTP_FROM_EMAIL")
        from_name: str = Field("ACGS-2 Audit Service", validation_alias="SMTP_FROM_NAME")
        timeout: float = Field(30.0, validation_alias="SMTP_TIMEOUT")
        enabled: bool = Field(False, validation_alias="SMTP_ENABLED")

    class SSOSettings(BaseSettings):
        """SSO and Authentication settings for OIDC and SAML 2.0."""

        enabled: bool = Field(True, validation_alias="SSO_ENABLED")
        session_lifetime_seconds: int = Field(3600, validation_alias="SSO_SESSION_LIFETIME")

        # OIDC settings
        oidc_enabled: bool = Field(True, validation_alias="OIDC_ENABLED")
        oidc_client_id: Optional[str] = Field(None, validation_alias="OIDC_CLIENT_ID")
        oidc_client_secret: Optional[SecretStr] = Field(None, validation_alias="OIDC_CLIENT_SECRET")
        oidc_issuer_url: Optional[str] = Field(None, validation_alias="OIDC_ISSUER_URL")
        oidc_scopes: List[str] = Field(
            ["openid", "email", "profile"], validation_alias="OIDC_SCOPES"
        )
        oidc_use_pkce: bool = Field(True, validation_alias="OIDC_USE_PKCE")

        # SAML settings
        saml_enabled: bool = Field(True, validation_alias="SAML_ENABLED")
        saml_entity_id: Optional[str] = Field(None, validation_alias="SAML_ENTITY_ID")
        saml_sign_requests: bool = Field(True, validation_alias="SAML_SIGN_REQUESTS")
        saml_want_assertions_signed: bool = Field(
            True, validation_alias="SAML_WANT_ASSERTIONS_SIGNED"
        )
        saml_want_assertions_encrypted: bool = Field(
            False, validation_alias="SAML_WANT_ASSERTIONS_ENCRYPTED"
        )
        saml_sp_certificate: Optional[str] = Field(None, validation_alias="SAML_SP_CERTIFICATE")
        saml_sp_private_key: Optional[SecretStr] = Field(
            None, validation_alias="SAML_SP_PRIVATE_KEY"
        )
        saml_idp_metadata_url: Optional[str] = Field(None, validation_alias="SAML_IDP_METADATA_URL")
        saml_idp_sso_url: Optional[str] = Field(None, validation_alias="SAML_IDP_SSO_URL")
        saml_idp_slo_url: Optional[str] = Field(None, validation_alias="SAML_IDP_SLO_URL")
        saml_idp_certificate: Optional[str] = Field(None, validation_alias="SAML_IDP_CERTIFICATE")

        # Provisioning
        auto_provision_users: bool = Field(True, validation_alias="SSO_AUTO_PROVISION")
        default_role_on_provision: str = Field("viewer", validation_alias="SSO_DEFAULT_ROLE")
        allowed_domains: Optional[List[str]] = Field(None, validation_alias="SSO_ALLOWED_DOMAINS")

    class Settings(BaseSettings):
        """Global Application Settings."""

        model_config = SettingsConfigDict(
            env_file=".env", env_file_encoding="utf-8", extra="ignore"
        )

        env: str = Field("development", validation_alias="APP_ENV")
        debug: bool = Field(False, validation_alias="APP_DEBUG")

        redis: RedisSettings = RedisSettings()
        ai: AISettings = AISettings()
        blockchain: BlockchainSettings = BlockchainSettings()
        security: SecuritySettings = SecuritySettings()
        sso: SSOSettings = SSOSettings()
        smtp: SMTPSettings = SMTPSettings()
        opa: OPASettings = OPASettings()
        audit: AuditSettings = AuditSettings()
        bundle: BundleSettings = BundleSettings()
        services: ServiceSettings = ServiceSettings()
        telemetry: TelemetrySettings = TelemetrySettings()
        aws: AWSSettings = AWSSettings()
        search_platform: SearchPlatformSettings = SearchPlatformSettings()
        quality: QualitySettings = QualitySettings()
        maci: MACISettings = MACISettings()
        vault: VaultSettings = VaultSettings()
        voting: VotingSettings = VotingSettings()
        kafka: JSONDict = Field(
            default_factory=lambda: {
                "bootstrap_servers": os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
                "security_protocol": os.getenv("KAFKA_SECURITY_PROTOCOL", "PLAINTEXT"),
                "ssl_ca_location": os.getenv("KAFKA_SSL_CA_LOCATION"),
                "ssl_certificate_location": os.getenv("KAFKA_SSL_CERTIFICATE_LOCATION"),
                "ssl_key_location": os.getenv("KAFKA_SSL_KEY_LOCATION"),
                "ssl_password": os.getenv("KAFKA_SSL_PASSWORD"),
            },
            validation_alias="KAFKA_CONFIG",
        )

        @model_validator(mode="after")
        def validate_production_security(self) -> "Settings":
            """Ensure strict security when running in production."""
            if self.env == "production":
                if not self.security.jwt_secret:
                    raise ValueError("JWT_SECRET is mandatory in production environment")

                jwt_val = self.security.jwt_secret.get_secret_value()
                if jwt_val == "dev-secret":
                    raise ValueError("Insecure JWT_SECRET 'dev-secret' is forbidden in production")
                if len(jwt_val) < 32:
                    raise ValueError("JWT_SECRET must be at least 32 characters in production")

                if not self.security.api_key_internal:
                    raise ValueError("API_KEY_INTERNAL is mandatory in production environment")
                if self.security.jwt_public_key == "SYSTEM_PUBLIC_KEY_PLACEHOLDER":
                    raise ValueError("JWT_PUBLIC_KEY must be configured in production environment")
            return self

else:
    # Fallback to pure os.getenv for environment mapping
    from dataclasses import dataclass, field
    from typing import Any, Dict

    @dataclass
    class RedisSettings:
        url: str = field(default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379"))
        host: str = field(default_factory=lambda: os.getenv("REDIS_HOST", "localhost"))
        port: int = field(default_factory=lambda: int(os.getenv("REDIS_PORT", "6379")))
        db: int = field(default_factory=lambda: int(os.getenv("REDIS_DB", "0")))
        max_connections: int = field(
            default_factory=lambda: int(os.getenv("REDIS_MAX_CONNECTIONS", "100"))
        )
        socket_timeout: float = field(
            default_factory=lambda: float(os.getenv("REDIS_SOCKET_TIMEOUT", "5.0"))
        )
        retry_on_timeout: bool = field(
            default_factory=lambda: os.getenv("REDIS_RETRY_ON_TIMEOUT", "true").lower() == "true"
        )
        ssl: bool = field(default_factory=lambda: os.getenv("REDIS_SSL", "false").lower() == "true")
        ssl_cert_reqs: str = field(default_factory=lambda: os.getenv("REDIS_SSL_CERT_REQS", "none"))
        ssl_ca_certs: Optional[str] = field(default_factory=lambda: os.getenv("REDIS_SSL_CA_CERTS"))
        socket_keepalive: bool = field(
            default_factory=lambda: os.getenv("REDIS_SOCKET_KEEPALIVE", "true").lower() == "true"
        )
        health_check_interval: int = field(
            default_factory=lambda: int(os.getenv("REDIS_HEALTH_CHECK_INTERVAL", "30"))
        )

    @dataclass
    class AISettings:
        openrouter_api_key: Optional[SecretStr] = field(
            default_factory=lambda: (
                SecretStr(os.getenv("OPENROUTER_API_KEY", ""))
                if os.getenv("OPENROUTER_API_KEY")
                else None
            )
        )
        hf_token: Optional[SecretStr] = field(
            default_factory=lambda: (
                SecretStr(os.getenv("HF_TOKEN", "")) if os.getenv("HF_TOKEN") else None
            )
        )
        openai_api_key: Optional[SecretStr] = field(
            default_factory=lambda: (
                SecretStr(os.getenv("OPENAI_API_KEY", "")) if os.getenv("OPENAI_API_KEY") else None
            )
        )
        constitutional_hash: str = field(
            default_factory=lambda: os.getenv("CONSTITUTIONAL_HASH", "cdd01ef066bc6cf2")
        )

    @dataclass
    class BlockchainSettings:
        eth_l2_network: str = field(default_factory=lambda: os.getenv("ETH_L2_NETWORK", "optimism"))
        eth_rpc_url: str = field(
            default_factory=lambda: os.getenv("ETH_RPC_URL", "https://mainnet.optimism.io")
        )
        contract_address: Optional[str] = field(
            default_factory=lambda: os.getenv("AUDIT_CONTRACT_ADDRESS")
        )
        private_key: Optional[SecretStr] = field(
            default_factory=lambda: (
                SecretStr(os.getenv("BLOCKCHAIN_PRIVATE_KEY", ""))
                if os.getenv("BLOCKCHAIN_PRIVATE_KEY")
                else None
            )
        )

    @dataclass
    class SecuritySettings:
        api_key_internal: Optional[SecretStr] = field(
            default_factory=lambda: (
                SecretStr(os.getenv("API_KEY_INTERNAL", ""))
                if os.getenv("API_KEY_INTERNAL")
                else None
            )
        )
        cors_origins: List[str] = field(
            default_factory=lambda: os.getenv("CORS_ORIGINS", "*").split(",")
        )
        jwt_secret: Optional[SecretStr] = field(
            default_factory=lambda: (
                SecretStr(os.getenv("JWT_SECRET", "")) if os.getenv("JWT_SECRET") else None
            )
        )
        jwt_public_key: str = field(
            default_factory=lambda: os.getenv("JWT_PUBLIC_KEY", "SYSTEM_PUBLIC_KEY_PLACEHOLDER")
        )
        admin_api_key: Optional[SecretStr] = field(
            default_factory=lambda: (
                SecretStr(os.getenv("ADMIN_API_KEY", "")) if os.getenv("ADMIN_API_KEY") else None
            )
        )

    @dataclass
    class OPASettings:
        url: str = field(default_factory=lambda: os.getenv("OPA_URL", "http://localhost:8181"))
        mode: str = field(default_factory=lambda: os.getenv("OPA_MODE", "http"))
        fail_closed: bool = True
        ssl_verify: bool = field(
            default_factory=lambda: os.getenv("OPA_SSL_VERIFY", "true").lower() == "true"
        )
        ssl_cert: Optional[str] = field(default_factory=lambda: os.getenv("OPA_SSL_CERT"))
        ssl_key: Optional[str] = field(default_factory=lambda: os.getenv("OPA_SSL_KEY"))

    @dataclass
    class AuditSettings:
        url: str = field(
            default_factory=lambda: os.getenv("AUDIT_SERVICE_URL", "http://localhost:8001")
        )

    @dataclass
    class BundleSettings:
        registry_url: str = field(
            default_factory=lambda: os.getenv("BUNDLE_REGISTRY_URL", "http://localhost:5000")
        )
        storage_path: str = field(
            default_factory=lambda: os.getenv("BUNDLE_STORAGE_PATH", "./storage/bundles")
        )
        s3_bucket: Optional[str] = field(default_factory=lambda: os.getenv("BUNDLE_S3_BUCKET"))
        github_webhook_secret: Optional[SecretStr] = field(
            default_factory=lambda: (
                SecretStr(os.getenv("GITHUB_WEBHOOK_SECRET", ""))
                if os.getenv("GITHUB_WEBHOOK_SECRET")
                else None
            )
        )

    @dataclass
    class ServiceSettings:
        agent_bus_url: str = field(
            default_factory=lambda: os.getenv("AGENT_BUS_URL", "http://localhost:8000")
        )
        policy_registry_url: str = field(
            default_factory=lambda: os.getenv("POLICY_REGISTRY_URL", "http://localhost:8000")
        )
        api_gateway_url: str = field(
            default_factory=lambda: os.getenv("API_GATEWAY_URL", "http://localhost:8080")
        )
        tenant_management_url: str = field(
            default_factory=lambda: os.getenv("TENANT_MANAGEMENT_URL", "http://localhost:8500")
        )
        hitl_approvals_url: str = field(
            default_factory=lambda: os.getenv("HITL_APPROVALS_URL", "http://localhost:8200")
        )
        ml_governance_url: str = field(
            default_factory=lambda: os.getenv("ML_GOVERNANCE_URL", "http://localhost:8400")
        )
        compliance_docs_url: str = field(
            default_factory=lambda: os.getenv("COMPLIANCE_DOCS_URL", "http://localhost:8100")
        )
        audit_service_url: str = field(
            default_factory=lambda: os.getenv("AUDIT_SERVICE_URL", "http://localhost:8300")
        )

    @dataclass
    class TelemetrySettings:
        otlp_endpoint: str = field(
            default_factory=lambda: os.getenv(
                "OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"
            )
        )
        service_name: str = field(default_factory=lambda: os.getenv("OTEL_SERVICE_NAME", "acgs2"))
        export_traces: bool = field(
            default_factory=lambda: os.getenv("OTEL_EXPORT_TRACES", "true").lower() == "true"
        )
        export_metrics: bool = field(
            default_factory=lambda: os.getenv("OTEL_EXPORT_METRICS", "true").lower() == "true"
        )
        trace_sample_rate: float = field(
            default_factory=lambda: float(os.getenv("OTEL_TRACE_SAMPLE_RATE", "1.0"))
        )

    @dataclass
    class AWSSettings:
        access_key_id: Optional[SecretStr] = field(
            default_factory=lambda: (
                SecretStr(os.getenv("AWS_ACCESS_KEY_ID", ""))
                if os.getenv("AWS_ACCESS_KEY_ID")
                else None
            )
        )
        secret_access_key: Optional[SecretStr] = field(
            default_factory=lambda: (
                SecretStr(os.getenv("AWS_SECRET_ACCESS_KEY", ""))
                if os.getenv("AWS_SECRET_ACCESS_KEY")
                else None
            )
        )
        region: str = field(default_factory=lambda: os.getenv("AWS_REGION", "us-east-1"))
        s3_endpoint_url: Optional[str] = field(default_factory=lambda: os.getenv("S3_ENDPOINT_URL"))

    @dataclass
    class SearchPlatformSettings:
        url: str = field(
            default_factory=lambda: os.getenv("SEARCH_PLATFORM_URL", "http://localhost:9080")
        )
        timeout_seconds: float = field(
            default_factory=lambda: float(os.getenv("SEARCH_PLATFORM_TIMEOUT", "30.0"))
        )
        max_connections: int = field(
            default_factory=lambda: int(os.getenv("SEARCH_PLATFORM_MAX_CONNECTIONS", "100"))
        )
        max_retries: int = field(
            default_factory=lambda: int(os.getenv("SEARCH_PLATFORM_MAX_RETRIES", "3"))
        )
        retry_delay_seconds: float = field(
            default_factory=lambda: float(os.getenv("SEARCH_PLATFORM_RETRY_DELAY", "1.0"))
        )
        circuit_breaker_threshold: int = field(
            default_factory=lambda: int(os.getenv("SEARCH_PLATFORM_CIRCUIT_THRESHOLD", "5"))
        )
        circuit_breaker_timeout: float = field(
            default_factory=lambda: float(os.getenv("SEARCH_PLATFORM_CIRCUIT_TIMEOUT", "30.0"))
        )
        enable_compliance: bool = field(
            default_factory=lambda: os.getenv("SEARCH_PLATFORM_ENABLE_COMPLIANCE", "true").lower()
            == "true"
        )

    @dataclass
    class QualitySettings:
        sonarqube_url: str = field(
            default_factory=lambda: os.getenv("SONARQUBE_URL", "http://localhost:9000")
        )
        sonarqube_token: Optional[SecretStr] = field(
            default_factory=lambda: (
                SecretStr(os.getenv("SONARQUBE_TOKEN", ""))
                if os.getenv("SONARQUBE_TOKEN")
                else None
            )
        )
        enable_local_analysis: bool = field(
            default_factory=lambda: os.getenv("QUALITY_ENABLE_LOCAL_ANALYSIS", "true").lower()
            == "true"
        )

    @dataclass
    class MACISettings:
        strict_mode: bool = field(
            default_factory=lambda: os.getenv("MACI_STRICT_MODE", "true").lower() == "true"
        )
        default_role: Optional[str] = field(default_factory=lambda: os.getenv("MACI_DEFAULT_ROLE"))
        config_path: Optional[str] = field(default_factory=lambda: os.getenv("MACI_CONFIG_PATH"))

    @dataclass
    class VaultSettings:
        address: str = field(
            default_factory=lambda: os.getenv("VAULT_ADDR", "http://127.0.0.1:8200")
        )
        token: Optional[SecretStr] = field(
            default_factory=lambda: (
                SecretStr(os.getenv("VAULT_TOKEN", "")) if os.getenv("VAULT_TOKEN") else None
            )
        )
        namespace: Optional[str] = field(default_factory=lambda: os.getenv("VAULT_NAMESPACE"))
        transit_mount: str = field(
            default_factory=lambda: os.getenv("VAULT_TRANSIT_MOUNT", "transit")
        )
        kv_mount: str = field(default_factory=lambda: os.getenv("VAULT_KV_MOUNT", "secret"))
        kv_version: int = field(default_factory=lambda: int(os.getenv("VAULT_KV_VERSION", "2")))
        timeout: float = field(default_factory=lambda: float(os.getenv("VAULT_TIMEOUT", "30.0")))
        verify_tls: bool = field(
            default_factory=lambda: os.getenv("VAULT_VERIFY_TLS", "true").lower() == "true"
        )
        ca_cert: Optional[str] = field(default_factory=lambda: os.getenv("VAULT_CACERT"))
        client_cert: Optional[str] = field(default_factory=lambda: os.getenv("VAULT_CLIENT_CERT"))
        client_key: Optional[str] = field(default_factory=lambda: os.getenv("VAULT_CLIENT_KEY"))

    @dataclass
    class VotingSettings:
        """Voting and deliberation settings for event-driven vote collection."""

        default_timeout_seconds: int = field(
            default_factory=lambda: int(os.getenv("VOTING_DEFAULT_TIMEOUT_SECONDS", "30"))
        )
        vote_topic_pattern: str = field(
            default_factory=lambda: os.getenv(
                "VOTING_VOTE_TOPIC_PATTERN", "acgs.tenant.{tenant_id}.votes"
            )
        )
        audit_topic_pattern: str = field(
            default_factory=lambda: os.getenv(
                "VOTING_AUDIT_TOPIC_PATTERN", "acgs.tenant.{tenant_id}.audit.votes"
            )
        )
        redis_election_prefix: str = field(
            default_factory=lambda: os.getenv("VOTING_REDIS_ELECTION_PREFIX", "election:")
        )
        enable_weighted_voting: bool = field(
            default_factory=lambda: os.getenv("VOTING_ENABLE_WEIGHTED", "true").lower() == "true"
        )
        signature_algorithm: str = field(
            default_factory=lambda: os.getenv("VOTING_SIGNATURE_ALGORITHM", "HMAC-SHA256")
        )
        audit_signature_key: Optional[SecretStr] = field(
            default_factory=lambda: (
                SecretStr(os.getenv("AUDIT_SIGNATURE_KEY", ""))
                if os.getenv("AUDIT_SIGNATURE_KEY")
                else None
            )
        )
        timeout_check_interval_seconds: int = field(
            default_factory=lambda: int(os.getenv("VOTING_TIMEOUT_CHECK_INTERVAL", "5"))
        )

    @dataclass
    class SMTPSettings:
        host: str = field(default_factory=lambda: os.getenv("SMTP_HOST", "localhost"))
        port: int = field(default_factory=lambda: int(os.getenv("SMTP_PORT", "587")))
        username: Optional[str] = field(default_factory=lambda: os.getenv("SMTP_USERNAME"))
        password: Optional[SecretStr] = field(
            default_factory=lambda: (
                SecretStr(os.getenv("SMTP_PASSWORD", "")) if os.getenv("SMTP_PASSWORD") else None
            )
        )
        use_tls: bool = field(
            default_factory=lambda: os.getenv("SMTP_USE_TLS", "true").lower() == "true"
        )
        use_ssl: bool = field(
            default_factory=lambda: os.getenv("SMTP_USE_SSL", "false").lower() == "true"
        )
        from_email: str = field(
            default_factory=lambda: os.getenv("SMTP_FROM_EMAIL", "noreply@acgs2.local")
        )
        from_name: str = field(
            default_factory=lambda: os.getenv("SMTP_FROM_NAME", "ACGS-2 Audit Service")
        )
        timeout: float = field(default_factory=lambda: float(os.getenv("SMTP_TIMEOUT", "30.0")))
        enabled: bool = field(
            default_factory=lambda: os.getenv("SMTP_ENABLED", "false").lower() == "true"
        )

    @dataclass
    class SSOSettings:
        enabled: bool = field(
            default_factory=lambda: os.getenv("SSO_ENABLED", "true").lower() == "true"
        )
        session_lifetime_seconds: int = field(
            default_factory=lambda: int(os.getenv("SSO_SESSION_LIFETIME", "3600"))
        )

        # OIDC
        oidc_enabled: bool = field(
            default_factory=lambda: os.getenv("OIDC_ENABLED", "true").lower() == "true"
        )
        oidc_client_id: Optional[str] = field(default_factory=lambda: os.getenv("OIDC_CLIENT_ID"))
        oidc_client_secret: Optional[SecretStr] = field(
            default_factory=lambda: (
                SecretStr(os.getenv("OIDC_CLIENT_SECRET", ""))
                if os.getenv("OIDC_CLIENT_SECRET")
                else None
            )
        )
        oidc_issuer_url: Optional[str] = field(default_factory=lambda: os.getenv("OIDC_ISSUER_URL"))
        oidc_scopes: List[str] = field(
            default_factory=lambda: os.getenv("OIDC_SCOPES", "openid,email,profile").split(",")
        )
        oidc_use_pkce: bool = field(
            default_factory=lambda: os.getenv("OIDC_USE_PKCE", "true").lower() == "true"
        )

        # SAML
        saml_enabled: bool = field(
            default_factory=lambda: os.getenv("SAML_ENABLED", "true").lower() == "true"
        )
        saml_entity_id: Optional[str] = field(default_factory=lambda: os.getenv("SAML_ENTITY_ID"))
        saml_sign_requests: bool = field(
            default_factory=lambda: os.getenv("SAML_SIGN_REQUESTS", "true").lower() == "true"
        )
        saml_want_assertions_signed: bool = field(
            default_factory=lambda: os.getenv("SAML_WANT_ASSERTIONS_SIGNED", "true").lower()
            == "true"
        )
        saml_want_assertions_encrypted: bool = field(
            default_factory=lambda: os.getenv("SAML_WANT_ASSERTIONS_ENCRYPTED", "false").lower()
            == "true"
        )
        saml_sp_certificate: Optional[str] = field(
            default_factory=lambda: os.getenv("SAML_SP_CERTIFICATE")
        )
        saml_sp_private_key: Optional[SecretStr] = field(
            default_factory=lambda: (
                SecretStr(os.getenv("SAML_SP_PRIVATE_KEY", ""))
                if os.getenv("SAML_SP_PRIVATE_KEY")
                else None
            )
        )
        saml_idp_metadata_url: Optional[str] = field(
            default_factory=lambda: os.getenv("SAML_IDP_METADATA_URL")
        )
        saml_idp_sso_url: Optional[str] = field(
            default_factory=lambda: os.getenv("SAML_IDP_SSO_URL")
        )
        saml_idp_slo_url: Optional[str] = field(
            default_factory=lambda: os.getenv("SAML_IDP_SLO_URL")
        )
        saml_idp_certificate: Optional[str] = field(
            default_factory=lambda: os.getenv("SAML_IDP_CERTIFICATE")
        )

        # Provisioning
        auto_provision_users: bool = field(
            default_factory=lambda: os.getenv("SSO_AUTO_PROVISION", "true").lower() == "true"
        )
        default_role_on_provision: str = field(
            default_factory=lambda: os.getenv("SSO_DEFAULT_ROLE", "viewer")
        )
        allowed_domains: Optional[List[str]] = field(
            default_factory=lambda: (
                os.getenv("SSO_ALLOWED_DOMAINS").split(",")
                if os.getenv("SSO_ALLOWED_DOMAINS")
                else None
            )
        )

    @dataclass
    class Settings:
        env: str = field(default_factory=lambda: os.getenv("APP_ENV", "development"))
        debug: bool = field(
            default_factory=lambda: os.getenv("APP_DEBUG", "false").lower() == "true"
        )

        redis: RedisSettings = field(default_factory=RedisSettings)
        ai: AISettings = field(default_factory=AISettings)
        blockchain: BlockchainSettings = field(default_factory=BlockchainSettings)
        security: SecuritySettings = field(default_factory=SecuritySettings)
        sso: SSOSettings = field(default_factory=SSOSettings)
        smtp: SMTPSettings = field(default_factory=SMTPSettings)
        opa: OPASettings = field(default_factory=OPASettings)
        audit: AuditSettings = field(default_factory=AuditSettings)
        bundle: BundleSettings = field(default_factory=BundleSettings)
        services: ServiceSettings = field(default_factory=ServiceSettings)
        telemetry: TelemetrySettings = field(default_factory=TelemetrySettings)
        aws: AWSSettings = field(default_factory=AWSSettings)
        search_platform: SearchPlatformSettings = field(default_factory=SearchPlatformSettings)
        quality: QualitySettings = field(default_factory=QualitySettings)
        maci: MACISettings = field(default_factory=MACISettings)
        vault: VaultSettings = field(default_factory=VaultSettings)
        voting: VotingSettings = field(default_factory=VotingSettings)
        kafka: Dict[str, Any] = field(
            default_factory=lambda: {
                "bootstrap_servers": os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
                "security_protocol": os.getenv("KAFKA_SECURITY_PROTOCOL", "PLAINTEXT"),
                "ssl_ca_location": os.getenv("KAFKA_SSL_CA_LOCATION"),
                "ssl_certificate_location": os.getenv("KAFKA_SSL_CERTIFICATE_LOCATION"),
                "ssl_key_location": os.getenv("KAFKA_SSL_KEY_LOCATION"),
                "ssl_password": os.getenv("KAFKA_SSL_PASSWORD"),
            }
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached application settings singleton."""
    return Settings()


# Singleton instance for backwards compatibility
# Use get_settings() for dependency injection patterns
settings = get_settings()
