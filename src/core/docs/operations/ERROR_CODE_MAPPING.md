# ACGS-2 Error Code Mapping

**Constitutional Hash:** cdd01ef066bc6cf2
**Version:** 1.0.0
**Created:** 2026-01-03
**Status:** Complete
**Purpose:** Comprehensive mapping of all exceptions and failure scenarios to error codes

---

## Table of Contents

1. [Overview](#overview)
2. [ACGS-1xxx: Configuration Errors](#acgs-1xxx-configuration-errors)
3. [ACGS-2xxx: Authentication/Authorization](#acgs-2xxx-authenticationauthorization)
4. [ACGS-3xxx: Deployment/Infrastructure](#acgs-3xxx-deploymentinfrastructure)
5. [ACGS-4xxx: Service Integration](#acgs-4xxx-service-integration)
6. [ACGS-5xxx: Runtime Errors](#acgs-5xxx-runtime-errors)
7. [ACGS-6xxx: Constitutional/Governance](#acgs-6xxx-constitutionalgovernance)
8. [ACGS-7xxx: Performance/Resource](#acgs-7xxx-performanceresource)
9. [ACGS-8xxx: Platform-Specific](#acgs-8xxx-platform-specific)
10. [Mapping Summary](#mapping-summary)

---

## Overview

This document provides the complete mapping between:
- **137 exception classes** (from EXCEPTION_CATALOG.md)
- **50+ deployment failure scenarios** (from DEPLOYMENT_FAILURE_SCENARIOS.md)
- **Assigned error codes** (from ERROR_CODE_TAXONOMY.md)

### Mapping Methodology

Each exception/scenario is assigned an error code based on:
1. **Primary category** - Type of error (config, auth, deployment, etc.)
2. **Subcategory** - Specific area within category
3. **Severity** - Impact level (CRITICAL, HIGH, MEDIUM, LOW)
4. **Impact** - Deployment-blocking, service-unavailable, degraded, etc.

### Document Structure

For each error code, we provide:
- **Error Code**: ACGS-NNNN format
- **Exception Class**: Python exception class name(s)
- **Scenario**: Deployment failure scenario(s)
- **Severity**: Operational severity level
- **Impact**: Service impact classification
- **Location**: File path(s) where exception is defined

---

## ACGS-1xxx: Configuration Errors

### ACGS-10xx: General Configuration

#### ACGS-1001: ConfigurationError
- **Exception**: `ConfigurationError` (enhanced-agent-bus)
- **Severity**: HIGH
- **Impact**: Deployment-Blocking
- **Location**: `acgs2-core/enhanced_agent_bus/exceptions.py`
- **Description**: Generic configuration error, base class for config issues
- **Common Causes**:
  - Invalid configuration structure
  - Missing required configuration sections
  - Configuration validation failures

---

### ACGS-11xx: Environment Variables

#### ACGS-1101: MissingEnvironmentVariableError
- **Exception**: `MissingEnvironmentVariableError` (integration-service)
- **Scenario**: Missing environment variables (DEPLOYMENT_FAILURE_SCENARIOS.md #8.1)
- **Severity**: CRITICAL
- **Impact**: Deployment-Blocking
- **Description**: Required environment variable not set
- **Common Variables**:
  - `CONSTITUTIONAL_HASH` (critical)
  - `OPA_URL`
  - `REDIS_URL`
  - `REDIS_PASSWORD`
  - `KAFKA_BOOTSTRAP_SERVERS`
  - `DATABASE_URL`
- **Frequency**: Very Common

#### ACGS-1102: InvalidEnvironmentVariableError
- **Scenario**: Wrong URL scheme in environment variables
- **Severity**: HIGH
- **Impact**: Deployment-Blocking
- **Description**: Environment variable has invalid format or value
- **Common Causes**:
  - Invalid URL format
  - Type mismatch (string vs integer)
  - Value outside acceptable range

#### ACGS-1103: EnvironmentVariableTypeError
- **Severity**: HIGH
- **Impact**: Deployment-Blocking
- **Description**: Environment variable type does not match expected type
- **Common Causes**:
  - String provided where integer expected
  - Boolean value incorrectly formatted

---

### ACGS-12xx: Configuration Files

#### ACGS-1201: ConfigValidationError
- **Exception**: `ConfigValidationError` (integration-service)
- **Severity**: HIGH
- **Impact**: Deployment-Blocking
- **Location**: `integration-service/src/config/validation.py`
- **Description**: Configuration validation failed
- **Common Causes**:
  - Invalid URL format
  - Missing required fields
  - Invalid enum values
  - Regex pattern mismatch

#### ACGS-1202: ConfigFileNotFoundError
- **Scenario**: .env file missing or not loaded
- **Severity**: HIGH
- **Impact**: Deployment-Blocking
- **Description**: Required configuration file not found
- **Common Causes**:
  - .env file not in correct location
  - File not created from .env.example
  - Incorrect file path

#### ACGS-1203: ConfigSchemaValidationError
- **Severity**: HIGH
- **Impact**: Deployment-Blocking
- **Description**: Configuration does not match expected schema
- **Common Causes**:
  - Schema version mismatch
  - Required fields missing
  - Invalid field types

---

### ACGS-13xx: Constitutional Hash

#### ACGS-1301: ConstitutionalHashMismatchError
- **Exception**:
  - `ConstitutionalHashMismatchError` (enhanced-agent-bus)
  - `ConstitutionalHashMismatchError` (sdk)
- **Scenario**: Constitutional hash mismatch (DEPLOYMENT_FAILURE_SCENARIOS.md #3.2)
- **Severity**: CRITICAL
- **Impact**: Deployment-Blocking
- **Location**:
  - `acgs2-core/enhanced_agent_bus/exceptions.py`
  - `acgs2-core/sdk/python/acgs2_sdk/exceptions.py`
- **Description**: Constitutional hash validation failed
- **Expected Hash**: `cdd01ef066bc6cf2`
- **Common Causes**:
  - Wrong hash in .env file
  - Hash not set in environment
  - Kubernetes ConfigMap not updated
- **Frequency**: Common

#### ACGS-1302: ConstitutionalValidationError
- **Exception**: `ConstitutionalValidationError` (enhanced-agent-bus)
- **Severity**: CRITICAL
- **Impact**: Service-Unavailable
- **Location**: `acgs2-core/enhanced_agent_bus/exceptions.py`
- **Description**: Constitutional validation check failed
- **Common Causes**:
  - Validation rules not met
  - Constitutional compliance violation
  - Alignment check failures

---

### ACGS-14xx: Service-Specific Config

#### ACGS-1401: OPAConfigurationError
- **Scenario**: Wrong OPA_URL configuration
- **Severity**: CRITICAL
- **Impact**: Deployment-Blocking
- **Description**: OPA service configuration invalid
- **Common Causes**:
  - Using localhost instead of Docker network name
  - Incorrect port number
  - Missing protocol (http://)

#### ACGS-1402: KafkaConfigurationError
- **Scenario**: Wrong Kafka bootstrap servers configuration
- **Severity**: CRITICAL
- **Impact**: Deployment-Blocking
- **Description**: Kafka configuration invalid
- **Common Causes**:
  - Using host:port from wrong context
  - Incorrect listener configuration

#### ACGS-1403: DatabaseConfigurationError
- **Severity**: CRITICAL
- **Impact**: Deployment-Blocking
- **Description**: Database configuration invalid
- **Common Causes**:
  - Invalid connection string format
  - Wrong credentials
  - Database name incorrect

---

### ACGS-15xx: Security Configuration

#### ACGS-1501: TLSConfigurationError
- **Severity**: HIGH
- **Impact**: Service-Unavailable
- **Description**: TLS/SSL configuration invalid
- **Common Causes**:
  - Invalid certificate
  - Certificate chain incomplete
  - Private key mismatch

#### ACGS-1502: CORSConfigurationError
- **Scenario**: CORS policy misconfigured
- **Severity**: CRITICAL (Security)
- **Impact**: Security-Vulnerability
- **Location**: `acgs2-core/services/compliance_docs/src/main.py:25`
- **Description**: CORS policy misconfigured. Use centralized `get_cors_config()`.
- **Status**: RESOLVED
- **Security Impact**: Allows any origin to access API

#### ACGS-1503: SecretNotFoundError
- **Severity**: CRITICAL
- **Impact**: Deployment-Blocking
- **Description**: Required secret not found in secret store
- **Common Causes**:
  - Kubernetes secret not created
  - Secret key name mismatch
  - Vault/AWS Secrets Manager misconfiguration

#### ACGS-1504: OIDCConfigurationError
- **Exception**: `OIDCConfigurationError` (shared-auth)
- **Severity**: HIGH
- **Impact**: Service-Unavailable
- **Location**: `acgs2-core/shared/auth/oidc_handler.py`
- **Description**: OIDC provider configuration error
- **Common Causes**:
  - Missing client ID or secret
  - Invalid discovery URL
  - Provider not registered

#### ACGS-1505: SAMLConfigurationError
- **Exception**: `SAMLConfigurationError` (shared-auth)
- **Severity**: HIGH
- **Impact**: Service-Unavailable
- **Location**: `acgs2-core/shared/auth/saml_config.py`
- **Description**: SAML configuration error
- **Common Causes**:
  - Invalid IdP metadata
  - Certificate issues
  - SP configuration mismatch

---

## ACGS-2xxx: Authentication/Authorization

### ACGS-20xx: General Auth/Authz

#### ACGS-2001: AuthenticationError
- **Exception**:
  - `AuthenticationError` (integration-service integrations)
  - `AuthenticationError` (sdk)
- **Severity**: HIGH
- **Impact**: Service-Unavailable
- **Location**:
  - `integration-service/src/integrations/base.py`
  - `acgs2-core/sdk/python/acgs2_sdk/exceptions.py`
- **Description**: Generic authentication failure

#### ACGS-2002: AuthorizationError
- **Exception**: `AuthorizationError` (sdk)
- **Severity**: HIGH
- **Impact**: Service-Unavailable
- **Location**: `acgs2-core/sdk/python/acgs2_sdk/exceptions.py`
- **Description**: Authorization denied

#### ACGS-2003: AccessDeniedError
- **Exception**:
  - `AccessDeniedError` (tenant-management)
  - `AccessDeniedError` (tenant-integration)
- **Severity**: HIGH
- **Impact**: Service-Degraded
- **Description**: Tenant access denied

---

### ACGS-21xx: Webhook Authentication

#### ACGS-2101: InvalidSignatureError
- **Exception**: `InvalidSignatureError` (integration-service)
- **Scenario**: Webhook signature verification fails
- **Severity**: HIGH
- **Impact**: Service-Degraded
- **Location**: `integration-service/src/webhooks/auth.py`
- **Description**: HMAC signature verification failed
- **Common Causes**:
  - Incorrect secret key
  - Signature algorithm mismatch
  - Payload tampering
  - Timestamp mismatch in signed payload
- **Frequency**: Common

#### ACGS-2102: InvalidApiKeyError
- **Exception**: `InvalidApiKeyError` (integration-service)
- **Severity**: HIGH
- **Impact**: Service-Degraded
- **Location**: `integration-service/src/webhooks/auth.py`
- **Description**: API key validation failed
- **Common Causes**:
  - Missing API key header
  - Invalid or revoked API key
  - Key not registered in handler

#### ACGS-2103: InvalidBearerTokenError
- **Exception**: `InvalidBearerTokenError` (integration-service)
- **Severity**: HIGH
- **Impact**: Service-Degraded
- **Location**: `integration-service/src/webhooks/auth.py`
- **Description**: Bearer token invalid
- **Common Causes**:
  - Expired token
  - Invalid token format
  - Token not in token store

#### ACGS-2104: TokenExpiredError
- **Exception**: `TokenExpiredError` (integration-service)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Location**: `integration-service/src/webhooks/auth.py`
- **Description**: OAuth token expired
- **Common Causes**:
  - Token TTL exceeded
  - System clock drift

#### ACGS-2105: SignatureTimestampError
- **Exception**: `SignatureTimestampError` (integration-service)
- **Severity**: HIGH
- **Impact**: Service-Degraded
- **Location**: `integration-service/src/webhooks/auth.py`
- **Description**: Signature timestamp outside acceptable window (default 300s)
- **Common Causes**:
  - Request replay attack
  - Clock skew between systems
  - Network delay > tolerance

#### ACGS-2106: MissingAuthHeaderError
- **Exception**: `MissingAuthHeaderError` (integration-service)
- **Severity**: HIGH
- **Impact**: Service-Degraded
- **Location**: `integration-service/src/webhooks/auth.py`
- **Description**: Required authentication header missing

#### ACGS-2107: WebhookAuthError
- **Exception**: `WebhookAuthError` (integration-service)
- **Severity**: HIGH
- **Impact**: Service-Degraded
- **Location**: `integration-service/src/webhooks/auth.py`
- **Description**: Base exception for webhook authentication errors

#### ACGS-2108: WebhookAuthenticationError
- **Exception**: `WebhookAuthenticationError` (integration-service)
- **Severity**: HIGH
- **Impact**: Service-Degraded
- **Location**: `integration-service/src/webhooks/delivery.py`
- **Description**: Webhook delivery authentication failed

---

### ACGS-22xx: SSO/Identity Providers

#### ACGS-2201: OIDCAuthenticationError
- **Exception**: `OIDCAuthenticationError` (shared-auth)
- **Severity**: HIGH
- **Impact**: Service-Unavailable
- **Location**: `acgs2-core/shared/auth/oidc_handler.py`
- **Description**: OIDC authentication failed
- **Common Causes**:
  - Invalid authorization code
  - State parameter mismatch
  - User denied consent

#### ACGS-2202: OIDCTokenError
- **Exception**: `OIDCTokenError` (shared-auth)
- **Severity**: HIGH
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/shared/auth/oidc_handler.py`
- **Description**: OIDC token exchange or validation failed
- **Common Causes**:
  - Invalid token signature
  - Expired token
  - Token issuer mismatch

#### ACGS-2203: OIDCProviderError
- **Exception**: `OIDCProviderError` (shared-auth)
- **Severity**: HIGH
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/shared/auth/oidc_handler.py`
- **Description**: Error communicating with OIDC provider
- **Common Causes**:
  - Network connectivity issues
  - Provider unavailable
  - Invalid provider response

#### ACGS-2204: OIDCError
- **Exception**: `OIDCError` (shared-auth)
- **Severity**: HIGH
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/shared/auth/oidc_handler.py`
- **Description**: Base exception for OIDC-related errors

#### ACGS-2211: SAMLAuthenticationError
- **Exception**: `SAMLAuthenticationError` (shared-auth)
- **Severity**: HIGH
- **Impact**: Service-Unavailable
- **Location**: `acgs2-core/shared/auth/saml_handler.py`
- **Description**: SAML authentication failed

#### ACGS-2212: SAMLValidationError
- **Exception**: `SAMLValidationError` (shared-auth)
- **Severity**: HIGH
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/shared/auth/saml_handler.py`
- **Description**: SAML assertion validation failed

#### ACGS-2213: SAMLProviderError
- **Exception**: `SAMLProviderError` (shared-auth)
- **Severity**: HIGH
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/shared/auth/saml_handler.py`
- **Description**: Error communicating with SAML IdP

#### ACGS-2214: SAMLReplayError
- **Exception**: `SAMLReplayError` (shared-auth)
- **Severity**: CRITICAL (Security)
- **Impact**: Security-Vulnerability
- **Location**: `acgs2-core/shared/auth/saml_handler.py`
- **Description**: SAML replay attack detected

#### ACGS-2215: SAMLError
- **Exception**: `SAMLError` (shared-auth)
- **Severity**: HIGH
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/shared/auth/saml_handler.py`
- **Description**: Base exception for SAML-related errors

#### ACGS-2221: AzureADAuthError
- **Exception**: `AzureADAuthError` (identity-service)
- **Severity**: HIGH
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/services/identity/connectors/azure_ad_connector.py`
- **Description**: Azure AD authentication error

#### ACGS-2222: AzureADConfigError
- **Exception**: `AzureADConfigError` (identity-service)
- **Severity**: HIGH
- **Impact**: Deployment-Blocking
- **Location**: `acgs2-core/services/identity/connectors/azure_ad_connector.py`
- **Description**: Azure AD configuration error

#### ACGS-2223: AzureADGraphError
- **Exception**: `AzureADGraphError` (identity-service)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/services/identity/connectors/azure_ad_connector.py`
- **Description**: Azure AD Graph API error

#### ACGS-2224: AzureADError
- **Exception**: `AzureADError` (identity-service)
- **Severity**: HIGH
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/services/identity/connectors/azure_ad_connector.py`
- **Description**: Base exception for Azure AD errors

#### ACGS-2231: OktaAuthError
- **Exception**: `OktaAuthError` (identity-service)
- **Severity**: HIGH
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/services/identity/connectors/okta_models.py`
- **Description**: Okta authentication error

#### ACGS-2232: OktaConfigError
- **Exception**: `OktaConfigError` (identity-service)
- **Severity**: HIGH
- **Impact**: Deployment-Blocking
- **Location**: `acgs2-core/services/identity/connectors/okta_models.py`
- **Description**: Okta configuration error

#### ACGS-2233: OktaProvisioningError
- **Exception**: `OktaProvisioningError` (identity-service)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/services/identity/connectors/okta_models.py`
- **Description**: Okta user provisioning error

#### ACGS-2234: OktaGroupError
- **Exception**: `OktaGroupError` (identity-service)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/services/identity/connectors/okta_models.py`
- **Description**: Okta group operation error

---

### ACGS-23xx: Role-Based Access Control

#### ACGS-2301: RoleVerificationError
- **Scenario**: Role verification via OPA
- **Severity**: HIGH (Security)
- **Impact**: Security-Enforced
- **Location**: `acgs2-core/services/hitl_approvals/app/services/approval_chain_engine.py:148`
- **Description**: Role verification performed via OPA.
- **Status**: RESOLVED
- **Current Behavior**: Role verification implemented via OPA

#### ACGS-2302: InsufficientPermissionsError
- **Severity**: HIGH
- **Impact**: Service-Degraded
- **Description**: User lacks required permissions for operation

#### ACGS-2303: RoleMappingError
- **Exception**: `RoleMappingError` (shared-auth)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/shared/auth/role_mapper.py`
- **Description**: Role mapping failed

#### ACGS-2304: ProviderNotFoundError
- **Exception**: `ProviderNotFoundError` (shared-auth)
- **Severity**: HIGH
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/shared/auth/role_mapper.py`
- **Description**: Identity provider not found for role mapping

#### ACGS-2311: ProvisioningError
- **Exception**: `ProvisioningError` (shared-auth)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/shared/auth/provisioning.py`
- **Description**: Base exception for user provisioning errors

#### ACGS-2312: DomainNotAllowedError
- **Exception**: `DomainNotAllowedError` (shared-auth)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/shared/auth/provisioning.py`
- **Description**: User domain not in allowed list

#### ACGS-2313: ProvisioningDisabledError
- **Exception**: `ProvisioningDisabledError` (shared-auth)
- **Severity**: LOW
- **Impact**: Informational
- **Location**: `acgs2-core/shared/auth/provisioning.py`
- **Description**: Auto-provisioning is disabled

---

### ACGS-24xx: OPA Policy Evaluation

#### ACGS-2401: PolicyEvaluationError
- **Exception**:
  - `PolicyEvaluationError` (enhanced-agent-bus)
  - `PolicyEvaluationError` (hitl-approvals)
- **Scenario**: OPA policy evaluation fails
- **Severity**: HIGH
- **Impact**: Service-Degraded
- **Location**:
  - `acgs2-core/enhanced_agent_bus/exceptions.py`
  - `acgs2-core/services/hitl_approvals/app/core/opa_client.py`
- **Description**: OPA policy evaluation failed
- **Common Causes**:
  - Policy execution error
  - Invalid input data
  - Policy returns error result

#### ACGS-2402: PolicyNotFoundError
- **Exception**: `PolicyNotFoundError` (enhanced-agent-bus)
- **Scenario**: Policy query returns undefined
- **Severity**: HIGH
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/enhanced_agent_bus/exceptions.py`
- **Description**: Required policy not found in OPA
- **Common Causes**:
  - Wrong policy path
  - Policy not loaded
  - Policy compilation errors
- **Frequency**: Common

#### ACGS-2403: OPAConnectionError
- **Exception**:
  - `OPAConnectionError` (enhanced-agent-bus)
  - `OPAConnectionError` (hitl-approvals)
  - `OPAConnectionError` (cli)
- **Scenario**: Cannot connect to OPA (DEPLOYMENT_FAILURE_SCENARIOS.md #2.1)
- **Severity**: CRITICAL
- **Impact**: Service-Unavailable (Fail-Closed)
- **Location**:
  - `acgs2-core/enhanced_agent_bus/exceptions.py`
  - `acgs2-core/services/hitl_approvals/app/core/opa_client.py`
  - `acgs2-core/cli/opa_service.py`
- **Description**: Cannot connect to OPA server
- **Common Causes**:
  - OPA container not running
  - Wrong OPA_URL (localhost vs docker name)
  - Port 8181 not accessible
- **Frequency**: Common
- **Impact Note**: System fails closed - all requests denied

#### ACGS-2404: OPANotInitializedError
- **Exception**:
  - `OPANotInitializedError` (enhanced-agent-bus)
  - `OPANotInitializedError` (hitl-approvals)
- **Severity**: CRITICAL
- **Impact**: Service-Unavailable
- **Location**:
  - `acgs2-core/enhanced_agent_bus/exceptions.py`
  - `acgs2-core/services/hitl_approvals/app/core/opa_client.py`
- **Description**: OPA client not properly initialized

#### ACGS-2411: PolicyError
- **Exception**: `PolicyError` (enhanced-agent-bus)
- **Severity**: HIGH
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/enhanced_agent_bus/exceptions.py`
- **Description**: Base exception for policy-related errors

#### ACGS-2412: OPAClientError
- **Exception**: `OPAClientError` (hitl-approvals)
- **Severity**: HIGH
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/services/hitl_approvals/app/core/opa_client.py`
- **Description**: Base exception for OPA client errors

#### ACGS-2413: OPAServiceError
- **Exception**: `OPAServiceError` (cli)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/cli/opa_service.py`
- **Description**: Base exception for OPA service CLI errors

---

### ACGS-25xx: Token Management

#### ACGS-2501: TokenRefreshError
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Description**: Token refresh operation failed

#### ACGS-2502: TokenRevocationError
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Description**: Token revocation failed

---

## ACGS-3xxx: Deployment/Infrastructure

### ACGS-30xx: General Deployment

#### ACGS-3001: DeploymentError
- **Severity**: CRITICAL
- **Impact**: Deployment-Blocking
- **Description**: Generic deployment failure

---

### ACGS-31xx: Docker/Container

#### ACGS-3101: DockerDaemonNotRunningError
- **Scenario**: Docker daemon not running (DEPLOYMENT_FAILURE_SCENARIOS.md #1.1)
- **Severity**: CRITICAL
- **Impact**: Deployment-Blocking
- **Description**: Cannot connect to Docker daemon
- **Common Causes**:
  - Docker Desktop not started (macOS/Windows)
  - Docker systemd service stopped (Linux)
  - Docker socket permissions
- **Frequency**: Very Common (Development)

#### ACGS-3102: ContainerStartupError
- **Scenario**: Container fails to start (DEPLOYMENT_FAILURE_SCENARIOS.md #1.2)
- **Severity**: CRITICAL
- **Impact**: Service-Unavailable
- **Description**: Container failed to start
- **Common Causes**:
  - Missing environment variables
  - Port conflicts
  - Volume mount errors
  - Insufficient resources
- **Frequency**: Common

#### ACGS-3103: ImagePullError
- **Scenario**: Image pull failures (DEPLOYMENT_FAILURE_SCENARIOS.md #1.3)
- **Severity**: CRITICAL
- **Impact**: Deployment-Blocking
- **Description**: Failed to pull container image
- **Common Causes**:
  - Network connectivity issues
  - Registry authentication failures
  - Image tag/version mismatch
  - Proxy configuration issues
- **Frequency**: Occasional

#### ACGS-3104: VolumeMountError
- **Severity**: HIGH
- **Impact**: Deployment-Blocking
- **Description**: Volume mounting failed
- **Common Causes**:
  - Path doesn't exist
  - Permission denied
  - SELinux blocking mount

#### ACGS-3105: ContainerOOMError
- **Scenario**: Container resource exhaustion - OOM kills (DEPLOYMENT_FAILURE_SCENARIOS.md #1.4)
- **Severity**: HIGH
- **Impact**: Service-Crash
- **Description**: Container killed due to out-of-memory (exit code 137)
- **Common Causes**:
  - Memory limit too low
  - Memory leak
  - Excessive resource usage
- **Frequency**: Common (Production)

---

### ACGS-32xx: Network/Connectivity

#### ACGS-3201: NetworkConnectivityError
- **Severity**: CRITICAL
- **Impact**: Service-Unavailable
- **Description**: Network connectivity lost

#### ACGS-3202: DNSResolutionError
- **Severity**: HIGH
- **Impact**: Service-Degraded
- **Description**: DNS resolution failed

#### ACGS-3203: ProxyConfigurationError
- **Severity**: MEDIUM
- **Impact**: Deployment-Blocking
- **Description**: Proxy misconfigured

#### ACGS-3204: NetworkPartitionError
- **Scenario**: Network partition during chaos testing
- **Severity**: CRITICAL
- **Impact**: Service-Unavailable
- **Description**: Network partition detected
- **Common in**: Chaos engineering tests
- **Frequency**: Rare (Testing/Emergency)

---

### ACGS-33xx: Port Management

#### ACGS-3301: PortAlreadyInUseError
- **Scenario**: Port already in use (DEPLOYMENT_FAILURE_SCENARIOS.md #7.1)
- **Severity**: CRITICAL
- **Impact**: Deployment-Blocking
- **Description**: Port conflict detected
- **Common Ports**:
  - 8181: OPA
  - 8000: Agent Bus (macOS Airplay conflict)
  - 8080: API Gateway
  - 6379: Redis
  - 19092: Kafka
  - 5432: PostgreSQL
- **Frequency**: Very Common (Development)

#### ACGS-3302: PortBindingError
- **Severity**: CRITICAL
- **Impact**: Deployment-Blocking
- **Description**: Failed to bind to port
- **Common Causes**:
  - Insufficient permissions
  - Port reserved by system

#### ACGS-3303: PortAccessError
- **Scenario**: Cannot access services from host (DEPLOYMENT_FAILURE_SCENARIOS.md #7.2)
- **Severity**: MEDIUM
- **Impact**: Development-Issue
- **Description**: Cannot access service on port from host
- **Common Causes**:
  - Ports not exposed in docker-compose
  - Firewall blocking ports
  - Wrong URL scheme
- **Frequency**: Common (Development)

---

### ACGS-34xx: Kubernetes/Helm

#### ACGS-3401: PodCrashLoopBackOffError
- **Scenario**: Pod CrashLoopBackOff (DEPLOYMENT_FAILURE_SCENARIOS.md #10.1)
- **Severity**: CRITICAL
- **Impact**: Service-Unavailable
- **Description**: Kubernetes pod in crash loop
- **Common Causes**:
  - Application startup failure
  - Missing ConfigMap/Secret
  - Liveness probe failing
  - Resource constraints
- **Frequency**: Very Common (Kubernetes)

#### ACGS-3402: ImagePullBackOffError
- **Scenario**: ImagePullBackOff (DEPLOYMENT_FAILURE_SCENARIOS.md #10.4)
- **Severity**: CRITICAL
- **Impact**: Deployment-Blocking
- **Description**: Kubernetes cannot pull image
- **Common Causes**:
  - Image doesn't exist
  - Registry authentication failure
  - Wrong image tag
- **Frequency**: Common (Kubernetes)

#### ACGS-3403: PersistentVolumeError
- **Severity**: HIGH
- **Impact**: Deployment-Blocking
- **Description**: PersistentVolume/PersistentVolumeClaim issues
- **Common Causes**:
  - PVC not bound
  - StorageClass misconfigured
  - Insufficient storage

#### ACGS-3404: ServiceUnavailableError
- **Exception**: `ServiceUnavailableError` (sdk)
- **Severity**: CRITICAL
- **Impact**: Service-Unavailable
- **Location**: `acgs2-core/sdk/python/acgs2_sdk/exceptions.py`
- **Description**: Kubernetes service unavailable

---

### ACGS-35xx: Resource Limits

#### ACGS-3501: CPUExhaustionError
- **Severity**: HIGH
- **Impact**: Performance-Degradation
- **Description**: CPU limit reached

#### ACGS-3502: MemoryExhaustionError
- **Scenario**: Container resource exhaustion (DEPLOYMENT_FAILURE_SCENARIOS.md #1.4)
- **Severity**: HIGH
- **Impact**: Service-Crash
- **Description**: Memory limit reached

#### ACGS-3503: DiskFullError
- **Severity**: CRITICAL
- **Impact**: Service-Crash
- **Description**: Disk space exhausted

#### ACGS-3504: ConnectionPoolExhaustedError
- **Severity**: HIGH
- **Impact**: Service-Degraded
- **Description**: Connection pool full

---

### ACGS-36xx: Cloud Provider

#### ACGS-3601: AWSConfigurationError
- **Severity**: HIGH
- **Impact**: Deployment-Blocking
- **Description**: AWS-specific configuration error

#### ACGS-3602: GCPConfigurationError
- **Severity**: HIGH
- **Impact**: Deployment-Blocking
- **Description**: GCP-specific configuration error

#### ACGS-3603: AzureConfigurationError
- **Severity**: HIGH
- **Impact**: Deployment-Blocking
- **Description**: Azure-specific configuration error

---

## ACGS-4xxx: Service Integration

### ACGS-40xx: General Integration

#### ACGS-4001: IntegrationError
- **Exception**: `IntegrationError` (integration-service)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Location**: `integration-service/src/integrations/base.py`
- **Description**: Generic third-party integration error

#### ACGS-4002: IntegrationConnectionError
- **Exception**: `IntegrationConnectionError` (integration-service)
- **Severity**: HIGH
- **Impact**: Service-Degraded
- **Location**: `integration-service/src/integrations/base.py`
- **Description**: Connection to external service failed

#### ACGS-4003: SearchPlatformError
- **Exception**: `SearchPlatformError` (integration/search_platform)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/services/integration/search_platform/client.py`
- **Description**: Search platform integration error

---

### ACGS-41xx: Redis

#### ACGS-4101: RedisConnectionError
- **Exception**:
  - `RedisConnectionError` (hitl-approvals/escalation)
  - `RedisNotAvailableError` (hitl-approvals/audit)
- **Scenario**: Redis connection refused (DEPLOYMENT_FAILURE_SCENARIOS.md #5.1)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded (Cache unavailable)
- **Location**:
  - `acgs2-core/services/hitl_approvals/app/core/escalation.py`
  - `acgs2-core/services/hitl_approvals/app/audit/ledger.py`
- **Description**: Cannot connect to Redis
- **Common Causes**:
  - Redis container not running
  - Wrong connection URL
  - Port conflict (6379)
- **Frequency**: Common

#### ACGS-4102: RedisAuthenticationError
- **Scenario**: Redis authentication failed (DEPLOYMENT_FAILURE_SCENARIOS.md #5.2)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Description**: Redis authentication failed
- **Common Causes**:
  - Password mismatch
  - REDIS_PASSWORD != password in REDIS_URL
- **Frequency**: Common (Configuration)

#### ACGS-4103: RedisTimeoutError
- **Severity**: MEDIUM
- **Impact**: Performance-Degradation
- **Description**: Redis operation timeout

#### ACGS-4104: RedisKeyNotFoundError
- **Severity**: LOW
- **Impact**: Informational
- **Description**: Cache key not found (cache miss)

#### ACGS-4105: EscalationTimerError
- **Exception**: `EscalationTimerError` (hitl-approvals)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/services/hitl_approvals/app/core/escalation.py`
- **Description**: Escalation timer error (base)

#### ACGS-4106: TimerNotFoundError
- **Exception**: `TimerNotFoundError` (hitl-approvals)
- **Severity**: LOW
- **Impact**: Informational
- **Location**: `acgs2-core/services/hitl_approvals/app/core/escalation.py`
- **Description**: Escalation timer not found

---

### ACGS-42xx: Kafka

#### ACGS-4201: KafkaConnectionError
- **Exception**: `KafkaConnectionError` (hitl-approvals)
- **Scenario**: Kafka not ready (DEPLOYMENT_FAILURE_SCENARIOS.md #6.1)
- **Severity**: HIGH
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/services/hitl_approvals/app/core/kafka_client.py`
- **Description**: Kafka connection failed
- **Common Causes**:
  - Kafka container not running
  - Zookeeper not running
  - Wrong bootstrap servers
- **Frequency**: Common (Startup)

#### ACGS-4202: KafkaNotAvailableError
- **Exception**: `KafkaNotAvailableError` (hitl-approvals)
- **Severity**: HIGH
- **Impact**: Deployment-Blocking
- **Location**: `acgs2-core/services/hitl_approvals/app/core/kafka_client.py`
- **Description**: aiokafka library not installed

#### ACGS-4203: KafkaPublishError
- **Exception**: `KafkaPublishError` (hitl-approvals)
- **Severity**: HIGH
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/services/hitl_approvals/app/core/kafka_client.py`
- **Description**: Failed to publish message to Kafka

#### ACGS-4204: KafkaConsumerError
- **Severity**: HIGH
- **Impact**: Service-Degraded
- **Description**: Kafka consumer error

#### ACGS-4205: KafkaTopicNotFoundError
- **Severity**: HIGH
- **Impact**: Service-Degraded
- **Description**: Kafka topic doesn't exist

#### ACGS-4206: KafkaClientError
- **Exception**: `KafkaClientError` (hitl-approvals)
- **Severity**: HIGH
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/services/hitl_approvals/app/core/kafka_client.py`
- **Description**: Base exception for Kafka client errors

#### ACGS-4211: KafkaMirrorMakerError
- **Scenario**: Kafka MirrorMaker 2 failures (DEPLOYMENT_FAILURE_SCENARIOS.md #11.3)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Description**: MirrorMaker 2 connector failed
- **Common Causes**:
  - Network partition between regions
  - Connector configuration errors
  - Topic ACL issues
- **Frequency**: Occasional (Multi-Region)
- **RTO Target**: < 5 minutes

---

### ACGS-43xx: PostgreSQL

#### ACGS-4301: DatabaseConnectionError
- **Scenario**: Database connection failures (DEPLOYMENT_FAILURE_SCENARIOS.md #4.1, #10.2)
- **Severity**: CRITICAL
- **Impact**: Service-Unavailable
- **Description**: Database connection failed
- **Common Causes**:
  - Database service not running
  - Wrong connection string
  - Network connectivity issues
  - Connection pool exhaustion
- **Frequency**: Common

#### ACGS-4302: DatabaseQueryError
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Description**: Query execution failed

#### ACGS-4303: DatabaseTimeoutError
- **Severity**: HIGH
- **Impact**: Performance-Degradation
- **Description**: Database query timeout

#### ACGS-4304: DatabaseConstraintError
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Description**: Database constraint violation

#### ACGS-4305: DatabaseReplicationError
- **Scenario**: Database replication lag (DEPLOYMENT_FAILURE_SCENARIOS.md #4.2)
- **Severity**: HIGH
- **Impact**: Data-Loss-Risk
- **Description**: Database replication lag or failure
- **Common Causes**:
  - Network latency between regions
  - High write volume
  - Standby resource constraints
- **Critical Threshold**: > 1 minute lag
- **Frequency**: Occasional (Multi-Region)

#### ACGS-4311: DatabaseFailoverError
- **Scenario**: Database failover issues (DEPLOYMENT_FAILURE_SCENARIOS.md #4.3, #11.2)
- **Severity**: CRITICAL
- **Impact**: Service-Outage
- **Description**: Database failover failed
- **Common Causes**:
  - Standby won't promote
  - Connection errors after promotion
  - Split-brain scenarios
- **RTO Target**: < 15 minutes
- **RPO Target**: < 1 minute
- **Frequency**: Rare (Emergency)

---

### ACGS-44xx: OPA Integration

#### ACGS-4401: OPAIntegrationError
- **Severity**: HIGH
- **Impact**: Service-Degraded
- **Description**: OPA integration failed (distinct from ACGS-24xx auth errors)

#### ACGS-4402: OPAQueryError
- **Severity**: HIGH
- **Impact**: Service-Degraded
- **Description**: OPA query execution failed

#### ACGS-4403: OPATimeoutError
- **Severity**: HIGH
- **Impact**: Service-Degraded
- **Description**: OPA request timeout

#### ACGS-4404: OPAPolicyLoadError
- **Scenario**: Policy syntax errors (DEPLOYMENT_FAILURE_SCENARIOS.md #2.3)
- **Severity**: CRITICAL
- **Impact**: Deployment-Blocking
- **Description**: Failed to load policy into OPA
- **Common Causes**:
  - rego_parse_error
  - rego_type_error
  - rego_unsafe_var_error
  - Missing package declaration
- **Frequency**: Occasional

---

### ACGS-45xx: External APIs

#### ACGS-4501: ExternalAPIError
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Description**: External API request failed

#### ACGS-4502: ExternalAPITimeoutError
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Description**: External API timeout

#### ACGS-4503: ExternalAPIRateLimitError
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Description**: External API rate limit exceeded

---

### ACGS-46xx: Email/Notifications

#### ACGS-4601: EmailDeliveryError
- **Exception**: `EmailDeliveryError` (audit-service)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/services/audit_service/app/services/email_service.py`
- **Description**: Email delivery failed

#### ACGS-4602: SMTPConnectionError
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Description**: SMTP connection failed

#### ACGS-4603: EmailConfigurationError
- **Exception**: `EmailConfigurationError` (audit-service)
- **Severity**: HIGH
- **Impact**: Deployment-Blocking
- **Location**: `acgs2-core/services/audit_service/app/services/email_service.py`
- **Description**: Email service configuration error

#### ACGS-4604: EmailRetryExhaustedError
- **Exception**: `EmailRetryExhaustedError` (audit-service)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/services/audit_service/app/services/email_service.py`
- **Description**: Email delivery failed after all retries

---

## ACGS-5xxx: Runtime Errors

### ACGS-50xx: General Runtime

#### ACGS-5001: RuntimeError
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Description**: Generic runtime error

---

### ACGS-51xx: Approval Chain

#### ACGS-5101: ApprovalChainResolutionError
- **Scenario**: Dynamic chain resolution via OPA
- **Severity**: HIGH
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/services/hitl_approvals/app/api/approvals.py:34`
- **Description**: Cannot resolve approval chain.
- **Status**: RESOLVED
- **Current Behavior**: Dynamic OPA-based resolution implemented

#### ACGS-5102: ApprovalTimeoutError
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Description**: Approval request timeout

#### ACGS-5103: InvalidApprovalStateError
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Description**: Invalid approval state transition

#### ACGS-5104: EscalationError
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Description**: Approval escalation failed

#### ACGS-5105: ApprovalDelegationError
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Description**: Approval delegation failed

#### ACGS-5111: ApprovalEngineError
- **Exception**: `ApprovalEngineError` (hitl-approvals)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/services/hitl_approvals/app/core/approval_engine.py`
- **Description**: Base exception for approval engine errors

#### ACGS-5112: ApprovalNotFoundError
- **Exception**: `ApprovalNotFoundError` (hitl-approvals)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/services/hitl_approvals/app/core/approval_engine.py`
- **Description**: Approval request not found

#### ACGS-5113: ChainNotFoundError
- **Exception**: `ChainNotFoundError` (hitl-approvals)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/services/hitl_approvals/app/core/approval_engine.py`
- **Description**: Approval chain not found

#### ACGS-5114: ApprovalStateError
- **Exception**: `ApprovalStateError` (hitl-approvals)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/services/hitl_approvals/app/core/approval_engine.py`
- **Description**: Invalid approval state transition

---

### ACGS-52xx: Webhook Delivery

#### ACGS-5201: WebhookDeliveryError
- **Exception**: `WebhookDeliveryError` (integration-service)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Location**: `integration-service/src/webhooks/delivery.py`
- **Description**: Webhook delivery failed

#### ACGS-5202: WebhookTimeoutError
- **Exception**: `WebhookTimeoutError` (integration-service)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Location**: `integration-service/src/webhooks/delivery.py`
- **Description**: Webhook request timeout
- **Common Causes**:
  - Slow endpoint response
  - Network latency
  - Endpoint unavailable

#### ACGS-5203: WebhookRetryExhaustedError
- **Exception**: `WebhookRetryError` (integration-service)
- **Severity**: HIGH
- **Impact**: Service-Degraded
- **Location**: `integration-service/src/webhooks/retry.py`
- **Description**: Webhook failed after all retries

#### ACGS-5204: WebhookConfigurationError
- **Scenario**: WebhookDeliveryEngine integration
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Location**: `integration-service/src/api/webhooks.py:633`
- **Description**: Webhook misconfigured or integration not complete.
- **Status**: RESOLVED
- **Current Behavior**: Test delivery implemented via `WebhookDeliveryEngine`

#### ACGS-5211: WebhookConnectionError
- **Exception**: `WebhookConnectionError` (integration-service)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Location**: `integration-service/src/webhooks/delivery.py`
- **Description**: Connection to webhook endpoint failed

#### ACGS-5212: RetryableError
- **Exception**: `RetryableError` (integration-service)
- **Severity**: LOW
- **Impact**: Informational
- **Location**: `integration-service/src/webhooks/retry.py`
- **Description**: Transient error that should trigger retry

#### ACGS-5213: NonRetryableError
- **Exception**: `NonRetryableError` (integration-service)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Location**: `integration-service/src/webhooks/retry.py`
- **Description**: Permanent error that should not trigger retry

#### ACGS-5221: DeliveryError
- **Exception**: `DeliveryError` (integration-service integrations)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Location**: `integration-service/src/integrations/base.py`
- **Description**: Event delivery to third-party service failed

---

### ACGS-53xx: Message Processing

#### ACGS-5301: MessageValidationError
- **Exception**: `MessageValidationError` (enhanced-agent-bus)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/enhanced_agent_bus/exceptions.py`
- **Description**: Message validation failed

#### ACGS-5302: MessageDeliveryError
- **Exception**: `MessageDeliveryError` (enhanced-agent-bus)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/enhanced_agent_bus/exceptions.py`
- **Description**: Message delivery failed

#### ACGS-5303: MessageTimeoutError
- **Exception**: `MessageTimeoutError` (enhanced-agent-bus)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/enhanced_agent_bus/exceptions.py`
- **Description**: Message processing timeout

#### ACGS-5304: MessageRoutingError
- **Exception**: `MessageRoutingError` (enhanced-agent-bus)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/enhanced_agent_bus/exceptions.py`
- **Description**: Message routing failed

#### ACGS-5305: RateLimitExceededError
- **Exception**:
  - `RateLimitExceeded` (enhanced-agent-bus)
  - `RateLimitError` (integration-service)
  - `RateLimitError` (sdk)
  - `RateLimitExceededError` (acl-adapters)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Location**:
  - `acgs2-core/enhanced_agent_bus/exceptions.py`
  - `integration-service/src/integrations/base.py`
  - `acgs2-core/sdk/python/acgs2_sdk/exceptions.py`
  - `acgs2-core/enhanced_agent_bus/acl_adapters/base.py`
- **Description**: Rate limit exceeded

#### ACGS-5311: MessageError
- **Exception**: `MessageError` (enhanced-agent-bus)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/enhanced_agent_bus/exceptions.py`
- **Description**: Base exception for message-related errors

---

### ACGS-54xx: Policy Execution

#### ACGS-5401: PolicyExecutionError
- **Severity**: HIGH
- **Impact**: Service-Degraded
- **Description**: Policy execution failed at runtime

#### ACGS-5402: PolicyContextError
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Description**: Invalid policy context provided

#### ACGS-5403: PolicyResultError
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Description**: Unexpected policy result format

#### ACGS-5411: PolicyVerificationError
- **Exception**: `PolicyVerificationError` (breakthrough/policy)
- **Severity**: HIGH
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/breakthrough/policy/verified_policy_generator.py`
- **Description**: Policy verification failed

---

### ACGS-55xx: Workflow/State

#### ACGS-5501: InvalidStateTransitionError
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Description**: Invalid state machine transition

#### ACGS-5502: WorkflowError
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Description**: Workflow execution error

---

### ACGS-56xx: Data Validation

#### ACGS-5601: ValidationError
- **Exception**:
  - `ValidationError` (integration-service integrations)
  - `ValidationError` (sdk)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Location**:
  - `integration-service/src/integrations/base.py`
  - `acgs2-core/sdk/python/acgs2_sdk/exceptions.py`
- **Description**: Input validation failed

#### ACGS-5602: SchemaValidationError
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Description**: Schema validation failed

#### ACGS-5603: DataFormatError
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Description**: Invalid data format

#### ACGS-5611: TenantValidationError
- **Exception**: `TenantValidationError` (tenant-context)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/shared/security/tenant_context.py`
- **Description**: Tenant context validation error

---

## ACGS-6xxx: Constitutional/Governance

### ACGS-60xx: General Governance

#### ACGS-6001: GovernanceError
- **Exception**: `GovernanceError` (enhanced-agent-bus)
- **Severity**: HIGH
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/enhanced_agent_bus/exceptions.py`
- **Description**: Generic governance error

#### ACGS-6002: ImpactAssessmentError
- **Exception**: `ImpactAssessmentError` (enhanced-agent-bus)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/enhanced_agent_bus/exceptions.py`
- **Description**: Impact assessment operation failed

---

### ACGS-61xx: Constitutional Validation

#### ACGS-6101: ConstitutionalHashMismatchError
- **Note**: Mapped to ACGS-1301 (primary mapping in configuration category)
- **See**: ACGS-1301 for details

#### ACGS-6102: ConstitutionalValidationError
- **Note**: Mapped to ACGS-1302 (primary mapping in configuration category)
- **See**: ACGS-1302 for details

#### ACGS-6103: ConstitutionalUpdateError
- **Severity**: CRITICAL
- **Impact**: Service-Unavailable
- **Description**: Constitutional update operation failed

#### ACGS-6111: ConstitutionalError
- **Exception**: `ConstitutionalError` (enhanced-agent-bus)
- **Severity**: CRITICAL
- **Impact**: Service-Unavailable
- **Location**: `acgs2-core/enhanced_agent_bus/exceptions.py`
- **Description**: Base exception for constitutional compliance failures

---

### ACGS-62xx: MACI Role Separation

#### ACGS-6201: MACIRoleViolationError
- **Exception**: `MACIRoleViolationError` (enhanced-agent-bus)
- **Severity**: CRITICAL (Security)
- **Impact**: Security-Violation
- **Location**: `acgs2-core/enhanced_agent_bus/exceptions.py`
- **Description**: Agent attempted action outside its MACI role
- **Purpose**: Prevent unauthorized cross-role operations

#### ACGS-6202: MACISelfValidationError
- **Exception**: `MACISelfValidationError` (enhanced-agent-bus)
- **Severity**: CRITICAL (Security)
- **Impact**: Security-Violation (Gödel Bypass Prevention)
- **Location**: `acgs2-core/enhanced_agent_bus/exceptions.py`
- **Description**: Agent attempted to validate its own output (Gödel incompleteness bypass)
- **Prevention Type**: godel_bypass
- **Purpose**: Prevent self-certification (Gödel incompleteness theorem)

#### ACGS-6203: MACICrossRoleValidationError
- **Exception**: `MACICrossRoleValidationError` (enhanced-agent-bus)
- **Severity**: CRITICAL (Security)
- **Impact**: Security-Violation
- **Location**: `acgs2-core/enhanced_agent_bus/exceptions.py`
- **Description**: Cross-role validation constraints violated

#### ACGS-6204: MACIRoleNotAssignedError
- **Exception**: `MACIRoleNotAssignedError` (enhanced-agent-bus)
- **Severity**: HIGH
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/enhanced_agent_bus/exceptions.py`
- **Description**: Agent has no MACI role assigned

#### ACGS-6211: MACIError
- **Exception**: `MACIError` (enhanced-agent-bus)
- **Severity**: CRITICAL
- **Impact**: Security-Violation
- **Location**: `acgs2-core/enhanced_agent_bus/exceptions.py`
- **Description**: Base exception for MACI role separation errors

---

### ACGS-63xx: Deliberation

#### ACGS-6301: DeliberationTimeoutError
- **Exception**: `DeliberationTimeoutError` (enhanced-agent-bus)
- **Severity**: HIGH
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/enhanced_agent_bus/exceptions.py`
- **Description**: Deliberation process timed out

#### ACGS-6302: SignatureCollectionError
- **Exception**: `SignatureCollectionError` (enhanced-agent-bus)
- **Severity**: HIGH
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/enhanced_agent_bus/exceptions.py`
- **Description**: Multi-agent signature collection failed

#### ACGS-6303: ReviewConsensusError
- **Exception**: `ReviewConsensusError` (enhanced-agent-bus)
- **Severity**: HIGH
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/enhanced_agent_bus/exceptions.py`
- **Description**: Critic review consensus not reached

#### ACGS-6304: QuorumNotMetError
- **Severity**: HIGH
- **Impact**: Service-Degraded
- **Description**: Quorum requirements not satisfied

#### ACGS-6311: DeliberationError
- **Exception**: `DeliberationError` (enhanced-agent-bus)
- **Severity**: HIGH
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/enhanced_agent_bus/exceptions.py`
- **Description**: Base exception for deliberation layer errors

---

### ACGS-64xx: Alignment

#### ACGS-6401: AlignmentViolationError
- **Exception**: `AlignmentViolationError` (enhanced-agent-bus)
- **Severity**: CRITICAL
- **Impact**: Security-Violation
- **Location**: `acgs2-core/enhanced_agent_bus/exceptions.py`
- **Description**: Agent message/action violates constitutional alignment

#### ACGS-6402: SafetyConstraintError
- **Severity**: CRITICAL
- **Impact**: Security-Violation
- **Description**: Safety constraint violated

#### ACGS-6403: EthicalConstraintError
- **Severity**: CRITICAL
- **Impact**: Security-Violation
- **Description**: Ethical constraint violated

---

### ACGS-65xx: Audit/Compliance

#### ACGS-6501: AuditTrailError
- **Severity**: HIGH
- **Impact**: Compliance-Risk
- **Description**: Audit trail write failed

#### ACGS-6502: ComplianceViolationError
- **Severity**: CRITICAL
- **Impact**: Compliance-Risk
- **Description**: Compliance requirement violated

#### ACGS-6503: AuditIntegrityError
- **Exception**: `IntegrityError` (hitl-approvals/audit)
- **Severity**: CRITICAL
- **Impact**: Data-Integrity-Risk
- **Location**: `acgs2-core/services/hitl_approvals/app/audit/ledger.py`
- **Description**: Audit log integrity check failed

#### ACGS-6511: AuditLedgerError
- **Exception**: `AuditLedgerError` (hitl-approvals)
- **Scenario**: Audit ledger integration
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/services/hitl_approvals/app/audit/ledger.py`
- **Description**: Base exception for audit ledger errors.
- **Status**: RESOLVED
- **Recent Integration**:
  - `audit_service/app/api/governance.py` - KPI and Trend integration complete
  - `audit_service/app/tasks/report_tasks.py` - Audit log fetching complete

#### ACGS-6512: ImmutabilityError
- **Exception**: `ImmutabilityError` (hitl-approvals/audit)
- **Severity**: CRITICAL
- **Impact**: Data-Integrity-Risk
- **Location**: `acgs2-core/services/hitl_approvals/app/audit/ledger.py`
- **Description**: Immutability constraint violated

#### ACGS-6521: InvalidComplianceRequirementError
- **Exception**: `InvalidComplianceRequirementError` (tenant-management)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Description**: Compliance requirement is invalid

---

## ACGS-7xxx: Performance/Resource

### ACGS-70xx: General Performance

#### ACGS-7001: PerformanceError
- **Severity**: MEDIUM
- **Impact**: Performance-Degradation
- **Description**: Generic performance issue

---

### ACGS-71xx: Latency

#### ACGS-7101: LatencyThresholdExceededError
- **Scenario**: P99 latency > 5ms threshold (load testing)
- **Severity**: MEDIUM
- **Impact**: Performance-Degradation
- **Description**: P99 latency exceeds threshold
- **Threshold**: 5.0ms
- **Common Causes**:
  - OPA policy evaluation slow
  - Database query performance
  - Redis cache misses
  - Network latency

#### ACGS-7102: RequestTimeoutError
- **Severity**: HIGH
- **Impact**: Service-Degraded
- **Description**: Request processing timeout

#### ACGS-7103: SlowQueryError
- **Severity**: MEDIUM
- **Impact**: Performance-Degradation
- **Description**: Database query too slow

#### ACGS-7111: TimeoutError
- **Exception**: `TimeoutError` (sdk)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/sdk/python/acgs2_sdk/exceptions.py`
- **Description**: Request timeout (SDK)

#### ACGS-7112: LayerTimeoutError
- **Exception**: `LayerTimeoutError` (observability)
- **Severity**: MEDIUM
- **Impact**: Performance-Degradation
- **Location**: `acgs2-core/enhanced_agent_bus/observability/timeout_budget.py`
- **Description**: Timeout budget exceeded for observability layer

#### ACGS-7121: MLGovernanceTimeoutError
- **Exception**: `MLGovernanceTimeoutError` (enhanced-agent-bus)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/enhanced_agent_bus/integrations/ml_governance.py`
- **Description**: ML governance operation timeout

#### ACGS-7122: AdapterTimeoutError
- **Exception**: `AdapterTimeoutError` (acl-adapters)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/enhanced_agent_bus/acl_adapters/base.py`
- **Description**: ACL adapter operation timed out

---

### ACGS-72xx: Throughput

#### ACGS-7201: ThroughputLimitError
- **Scenario**: Throughput < 100 RPS threshold
- **Severity**: HIGH
- **Impact**: Performance-Degradation
- **Description**: Throughput below acceptable threshold
- **Threshold**: 100 RPS minimum

#### ACGS-7202: CapacityExceededError
- **Severity**: HIGH
- **Impact**: Service-Degraded
- **Description**: System capacity exceeded

#### ACGS-7203: BackpressureError
- **Severity**: MEDIUM
- **Impact**: Performance-Degradation
- **Description**: Backpressure applied due to overload

---

### ACGS-73xx: Resource Exhaustion

#### ACGS-7301: MemoryExhaustedError
- **Scenario**: OPA high memory usage (DEPLOYMENT_FAILURE_SCENARIOS.md #2.4)
- **Severity**: HIGH
- **Impact**: Service-Crash
- **Description**: Memory limit reached
- **Common Causes**:
  - Large policy bundles
  - Decision cache bloat
  - Memory leaks
- **Frequency**: Occasional (Production)

#### ACGS-7302: CPUThresholdExceededError
- **Severity**: HIGH
- **Impact**: Performance-Degradation
- **Description**: CPU usage too high

#### ACGS-7303: ConnectionLimitError
- **Severity**: HIGH
- **Impact**: Service-Degraded
- **Description**: Connection limit reached

#### ACGS-7304: ThreadPoolExhaustedError
- **Severity**: HIGH
- **Impact**: Service-Degraded
- **Description**: Thread pool full

#### ACGS-7311: QuotaExceededError
- **Exception**:
  - `QuotaExceededError` (tenant-management)
  - `QuotaExceededError` (tenant-integration)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Description**: Tenant quota limit exceeded

---

### ACGS-74xx: Circuit Breaker

#### ACGS-7401: CircuitBreakerOpenError
- **Scenario**: Circuit breaker opens due to failures (chaos testing)
- **Severity**: HIGH
- **Impact**: Service-Degraded
- **Description**: Circuit breaker in OPEN state
- **Common Triggers**:
  - 3 consecutive failures
  - Service unavailable
- **Recovery**: 30s backoff → HALF_OPEN

#### ACGS-7402: CircuitBreakerTimeoutError
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Description**: Circuit breaker timeout

#### ACGS-7411: AdapterCircuitOpenError
- **Exception**: `AdapterCircuitOpenError` (acl-adapters)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/enhanced_agent_bus/acl_adapters/base.py`
- **Description**: Circuit breaker is open for ACL adapter

---

### ACGS-75xx: Rate Limiting

#### ACGS-7501: RateLimitExceededError
- **Note**: See ACGS-5305 for primary mapping
- **Description**: Rate limit exceeded (cross-reference)

#### ACGS-7502: QuotaExceededError
- **Note**: See ACGS-7311 for primary mapping
- **Description**: Quota limit reached (cross-reference)

---

## ACGS-8xxx: Platform-Specific

### ACGS-80xx: General Platform

#### ACGS-8001: PlatformError
- **Severity**: MEDIUM
- **Impact**: Platform-Specific
- **Description**: Generic platform error

---

### ACGS-81xx: Windows/WSL2

#### ACGS-8101: WindowsLineEndingError
- **Scenario**: Line ending issues - CRLF vs LF (DEPLOYMENT_FAILURE_SCENARIOS.md #9.1)
- **Severity**: MEDIUM
- **Impact**: Development-Issue
- **Description**: Windows line ending (CRLF) breaking scripts
- **Common Causes**:
  - Git autocrlf=true
  - Files created in Windows
- **Solution**: `git config --global core.autocrlf input`, `dos2unix`
- **Frequency**: Common (Windows Development)

#### ACGS-8102: WSL2NetworkError
- **Severity**: MEDIUM
- **Impact**: Development-Issue
- **Description**: WSL2 networking issue

#### ACGS-8103: WindowsPathError
- **Severity**: MEDIUM
- **Impact**: Development-Issue
- **Description**: Windows path format error
- **Common Causes**:
  - Backslash vs forward slash
  - Volume mounting crossing Windows/WSL boundary

#### ACGS-8104: WindowsPermissionError
- **Severity**: MEDIUM
- **Impact**: Development-Issue
- **Description**: Windows file permissions issue

---

### ACGS-82xx: macOS

#### ACGS-8201: MacOSPortConflictError
- **Scenario**: Port 8000 conflict with Airplay (DEPLOYMENT_FAILURE_SCENARIOS.md #9.2)
- **Severity**: MEDIUM
- **Impact**: Deployment-Blocking
- **Description**: macOS-specific port conflict
- **Common Port**: 8000 (Airplay Receiver)
- **Solution**: Disable Airplay Receiver
- **Frequency**: Common (macOS Development)

#### ACGS-8202: MacOSDockerMemoryError
- **Severity**: MEDIUM
- **Impact**: Performance-Degradation
- **Description**: Docker Desktop memory allocation insufficient
- **Solution**: Increase Docker Desktop memory to 4GB+

#### ACGS-8203: MacOSFileWatchError
- **Severity**: LOW
- **Impact**: Development-Issue
- **Description**: File system watching issues (OSXFS)

---

### ACGS-83xx: Linux

#### ACGS-8301: LinuxPermissionError
- **Scenario**: Docker permission denied, file permissions (DEPLOYMENT_FAILURE_SCENARIOS.md #9.3)
- **Severity**: MEDIUM
- **Impact**: Deployment-Blocking
- **Description**: Linux file permissions issue
- **Common Causes**:
  - User not in docker group
  - File permissions on volumes
- **Solution**: `sudo usermod -aG docker $USER`
- **Frequency**: Common (Linux Development)

#### ACGS-8302: SELinuxPolicyError
- **Scenario**: SELinux blocking container operations
- **Severity**: MEDIUM
- **Impact**: Deployment-Blocking
- **Description**: SELinux policy blocking Docker operations
- **Solution**: Add `:Z` flag to volume mounts
- **Frequency**: Common (Linux)

#### ACGS-8303: CgroupLimitError
- **Severity**: MEDIUM
- **Impact**: Performance-Degradation
- **Description**: Cgroup resource limits reached

---

### ACGS-84xx: Container Runtime

#### ACGS-8401: ContainerRuntimeError
- **Severity**: HIGH
- **Impact**: Deployment-Blocking
- **Description**: Container runtime specific error

---

## ACGS-9xxx: Reserved for Future Use

### ACGS-90xx-99xx: Future Categories

Reserved for future error code categories not yet defined.

---

## Additional Exception Mappings

### Agent and Bus Operations

#### ACGS-5801: AgentError
- **Exception**: `AgentError` (enhanced-agent-bus)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/enhanced_agent_bus/exceptions.py`
- **Description**: Base exception for agent-related errors

#### ACGS-5802: AgentNotRegisteredError
- **Exception**: `AgentNotRegisteredError` (enhanced-agent-bus)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/enhanced_agent_bus/exceptions.py`
- **Description**: Operation requires registered agent that doesn't exist

#### ACGS-5803: AgentAlreadyRegisteredError
- **Exception**: `AgentAlreadyRegisteredError` (enhanced-agent-bus)
- **Severity**: LOW
- **Impact**: Informational
- **Location**: `acgs2-core/enhanced_agent_bus/exceptions.py`
- **Description**: Attempting to register agent that already exists

#### ACGS-5804: AgentCapabilityError
- **Exception**: `AgentCapabilityError` (enhanced-agent-bus)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/enhanced_agent_bus/exceptions.py`
- **Description**: Agent lacks required capabilities

#### ACGS-5811: BusOperationError
- **Exception**: `BusOperationError` (enhanced-agent-bus)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/enhanced_agent_bus/exceptions.py`
- **Description**: Base exception for bus operation errors

#### ACGS-5812: BusNotStartedError
- **Exception**: `BusNotStartedError` (enhanced-agent-bus)
- **Scenario**: Agent Bus not starting (DEPLOYMENT_FAILURE_SCENARIOS.md #3.1)
- **Severity**: CRITICAL
- **Impact**: Service-Unavailable
- **Location**: `acgs2-core/enhanced_agent_bus/exceptions.py`
- **Description**: Operation requires started bus
- **Common Causes**:
  - Dependencies not ready (OPA, Redis, Kafka)
  - Environment variable misconfiguration
  - Port already in use
- **Frequency**: Common

#### ACGS-5813: BusAlreadyStartedError
- **Exception**: `BusAlreadyStartedError` (enhanced-agent-bus)
- **Severity**: LOW
- **Impact**: Informational
- **Location**: `acgs2-core/enhanced_agent_bus/exceptions.py`
- **Description**: Attempting to start already running bus

#### ACGS-5814: HandlerExecutionError
- **Exception**: `HandlerExecutionError` (enhanced-agent-bus)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/enhanced_agent_bus/exceptions.py`
- **Description**: Message handler failed during execution

#### ACGS-5821: AgentBusError
- **Exception**: `AgentBusError` (enhanced-agent-bus)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/enhanced_agent_bus/exceptions.py`
- **Description**: Base exception for all Enhanced Agent Bus errors

---

### Tenant Management

#### ACGS-5831: TenantError
- **Exception**: `TenantError` (tenant-integration)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/shared/tenant_integration.py`
- **Description**: Base exception for tenant errors

#### ACGS-5832: TenantNotFoundError
- **Exception**:
  - `TenantNotFoundError` (tenant-management)
  - `TenantNotFoundError` (tenant-integration)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Description**: Tenant not found

#### ACGS-5833: TenantNotActiveError
- **Exception**: `TenantNotActiveError` (tenant-integration)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/shared/tenant_integration.py`
- **Description**: Tenant is not in active state

#### ACGS-5834: DuplicateTenantError
- **Exception**: `DuplicateTenantError` (tenant-management)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Description**: Attempting to create duplicate tenant

#### ACGS-5835: InvalidTenantOperationError
- **Exception**: `InvalidTenantOperationError` (tenant-management)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Description**: Invalid tenant operation

#### ACGS-5836: TenantIsolationError
- **Exception**: `TenantIsolationError` (tenant-management)
- **Severity**: CRITICAL (Security)
- **Impact**: Security-Violation
- **Description**: Tenant isolation boundary violated

---

### SDK Errors

#### ACGS-5841: ACGS2Error
- **Exception**: `ACGS2Error` (sdk)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/sdk/python/acgs2_sdk/exceptions.py`
- **Description**: Base exception for ACGS-2 SDK errors

#### ACGS-5842: NetworkError
- **Exception**: `NetworkError` (sdk)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/sdk/python/acgs2_sdk/exceptions.py`
- **Description**: Network error in SDK

#### ACGS-5843: ResourceNotFoundError
- **Exception**: `ResourceNotFoundError` (sdk)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/sdk/python/acgs2_sdk/exceptions.py`
- **Description**: Resource not found

#### ACGS-5844: ConflictError
- **Exception**: `ConflictError` (sdk)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/sdk/python/acgs2_sdk/exceptions.py`
- **Description**: Resource conflict occurred

---

### Recovery and ML Governance

#### ACGS-5851: RecoveryOrchestratorError
- **Exception**: `RecoveryOrchestratorError` (recovery-orchestrator)
- **Severity**: HIGH
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/enhanced_agent_bus/recovery_orchestrator.py`
- **Description**: Recovery orchestrator error

#### ACGS-5852: RecoveryConstitutionalError
- **Exception**: `RecoveryConstitutionalError` (recovery-orchestrator)
- **Severity**: CRITICAL
- **Impact**: Service-Unavailable
- **Location**: `acgs2-core/enhanced_agent_bus/recovery_orchestrator.py`
- **Description**: Constitutional error during recovery

#### ACGS-5853: RecoveryValidationError
- **Exception**: `RecoveryValidationError` (recovery-orchestrator)
- **Severity**: HIGH
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/enhanced_agent_bus/recovery_orchestrator.py`
- **Description**: Validation error during recovery

#### ACGS-5861: MLGovernanceError
- **Exception**: `MLGovernanceError` (enhanced-agent-bus)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/enhanced_agent_bus/integrations/ml_governance.py`
- **Description**: Base exception for ML governance errors

#### ACGS-5862: MLGovernanceConnectionError
- **Exception**: `MLGovernanceConnectionError` (enhanced-agent-bus)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/enhanced_agent_bus/integrations/ml_governance.py`
- **Description**: ML governance service connection error

---

### Cryptography and Temporal

#### ACGS-5871: FallbackCryptoError
- **Exception**: `FallbackCryptoError` (policy-registry)
- **Severity**: HIGH
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/services/policy_registry/app/services/secure_fallback_crypto.py`
- **Description**: Base exception for fallback crypto errors

#### ACGS-5872: KeyDerivationError
- **Exception**: `KeyDerivationError` (policy-registry)
- **Severity**: HIGH
- **Impact**: Security-Risk
- **Location**: `acgs2-core/services/policy_registry/app/services/secure_fallback_crypto.py`
- **Description**: Key derivation failed

#### ACGS-5873: EncryptionError
- **Exception**: `EncryptionError` (policy-registry)
- **Severity**: HIGH
- **Impact**: Security-Risk
- **Location**: `acgs2-core/services/policy_registry/app/services/secure_fallback_crypto.py`
- **Description**: Encryption operation failed

#### ACGS-5874: DecryptionError
- **Exception**: `DecryptionError` (policy-registry)
- **Severity**: HIGH
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/services/policy_registry/app/services/secure_fallback_crypto.py`
- **Description**: Decryption operation failed

#### ACGS-5875: CiphertextFormatError
- **Exception**: `CiphertextFormatError` (policy-registry)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/services/policy_registry/app/services/secure_fallback_crypto.py`
- **Description**: Invalid ciphertext format

#### ACGS-5876: CryptoNotAvailableError
- **Exception**: `CryptoNotAvailableError` (policy-registry)
- **Severity**: CRITICAL
- **Impact**: Deployment-Blocking
- **Location**: `acgs2-core/services/policy_registry/app/services/secure_fallback_crypto.py`
- **Description**: Cryptography library not available

#### ACGS-5881: TemporalViolationError
- **Exception**: `TemporalViolationError` (breakthrough/temporal)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/breakthrough/temporal/timeline_engine.py`
- **Description**: Temporal constraint violation

#### ACGS-5882: CausalViolationError
- **Exception**: `CausalViolationError` (breakthrough/temporal)
- **Severity**: MEDIUM
- **Impact**: Service-Degraded
- **Location**: `acgs2-core/breakthrough/temporal/timeline_engine.py`
- **Description**: Causal constraint violation

---

### Multi-Region Failover

#### ACGS-3701: ApplicationFailoverError
- **Scenario**: Application failover issues (DEPLOYMENT_FAILURE_SCENARIOS.md #11.1)
- **Severity**: HIGH
- **Impact**: Service-Interruption
- **Description**: Application-level failover failed
- **Common Causes**:
  - VirtualService weights not updating
  - Envoy proxy not reflecting changes
  - Service mesh connectivity issues
- **RTO Target**: < 60 seconds
- **Frequency**: Rare (Emergency)

#### ACGS-3702: RegionalSyncError
- **Severity**: HIGH
- **Impact**: Data-Consistency-Risk
- **Description**: Regional synchronization error

---

## Mapping Summary

### Total Mappings Created

- **Configuration Errors (ACGS-1xxx)**: 24 error codes
- **Authentication/Authorization (ACGS-2xxx)**: 53 error codes
- **Deployment/Infrastructure (ACGS-3xxx)**: 24 error codes
- **Service Integration (ACGS-4xxx)**: 29 error codes
- **Runtime Errors (ACGS-5xxx)**: 67 error codes
- **Constitutional/Governance (ACGS-6xxx)**: 22 error codes
- **Performance/Resource (ACGS-7xxx)**: 21 error codes
- **Platform-Specific (ACGS-8xxx)**: 10 error codes

**Total Error Codes Assigned**: 250+ codes

### Exception Coverage

- **Total Exceptions Mapped**: 137 of 137 (100%)
- **Deployment Scenarios Mapped**: 50+ of 50+ (100%)
- **TODO-Related Errors**: 10 of 10 (100%)

### Severity Distribution

- **CRITICAL**: ~45 error codes (18%)
- **HIGH**: ~95 error codes (38%)
- **MEDIUM**: ~90 error codes (36%)
- **LOW**: ~20 error codes (8%)

### Impact Distribution

- **Deployment-Blocking**: ~25 error codes (10%)
- **Service-Unavailable**: ~35 error codes (14%)
- **Service-Degraded**: ~120 error codes (48%)
- **Security-Violation**: ~15 error codes (6%)
- **Performance**: ~30 error codes (12%)
- **Informational**: ~25 error codes (10%)

---

## Cross-References

### Related Documentation

- **ERROR_CODE_TAXONOMY.md**: Defines error code structure and categories
- **EXCEPTION_CATALOG.md**: Complete catalog of 137 exception classes
- **DEPLOYMENT_FAILURE_SCENARIOS.md**: 50+ common deployment failure scenarios
- **GAP_ANALYSIS.md**: Documentation gaps and priorities
- **TODO_CATALOG.md**: TODO/FIXME comments creating error conditions

### Next Steps

1. **Phase 2.3**: Define severity levels for all error codes (refinement)
2. **Phase 3**: Create comprehensive ERROR_CODES.md with troubleshooting details
3. **Phase 6**: Update exception class docstrings with assigned error codes
4. **Phase 6**: Create searchable error code index

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-01-03 | Auto-Claude | Initial complete mapping of all 137 exceptions and 50+ scenarios |

---

**Constitutional Hash**: cdd01ef066bc6cf2
**Status**: ✅ Complete
**Next Phase**: 2.3 - Define error severity levels
