"""
ACGS-2 Identity Provider Connectors
Constitutional Hash: cdd01ef066bc6cf2

Enterprise identity provider integrations for federated authentication.
"""

from .okta_connector import (
    CONSTITUTIONAL_HASH,
    OktaConfig,
    OktaAuthError,
    OktaConfigError,
    OktaProvisioningError,
    OktaGroupError,
    OktaTokenType,
    OktaGrantType,
    OktaScope,
    OktaUserStatus,
    OktaTokenResponse,
    OktaUserInfo,
    OktaUser,
    OktaGroup,
    OktaAuthState,
    OktaOIDCConnector,
    get_okta_connector,
    configure_okta_connector,
    shutdown_okta_connector,
)

from .azure_ad_connector import (
    AzureADConfig,
    AzureADError,
    AzureADAuthError,
    AzureADConfigError,
    AzureADGraphError,
    AzureADCloud,
    AzureADGrantType,
    AzureADScope,
    AzureADUserType,
    AzureADTokenResponse,
    AzureADUserInfo,
    AzureADUser,
    AzureADGroup,
    AzureADAuthState,
    AzureADOIDCConnector,
    get_azure_ad_connector,
    configure_azure_ad_connector,
    shutdown_azure_ad_connector,
)

__all__ = [
    # Constitutional
    "CONSTITUTIONAL_HASH",

    # Okta
    "OktaConfig",
    "OktaAuthError",
    "OktaConfigError",
    "OktaProvisioningError",
    "OktaGroupError",
    "OktaTokenType",
    "OktaGrantType",
    "OktaScope",
    "OktaUserStatus",
    "OktaTokenResponse",
    "OktaUserInfo",
    "OktaUser",
    "OktaGroup",
    "OktaAuthState",
    "OktaOIDCConnector",
    "get_okta_connector",
    "configure_okta_connector",
    "shutdown_okta_connector",

    # Azure AD
    "AzureADConfig",
    "AzureADError",
    "AzureADAuthError",
    "AzureADConfigError",
    "AzureADGraphError",
    "AzureADCloud",
    "AzureADGrantType",
    "AzureADScope",
    "AzureADUserType",
    "AzureADTokenResponse",
    "AzureADUserInfo",
    "AzureADUser",
    "AzureADGroup",
    "AzureADAuthState",
    "AzureADOIDCConnector",
    "get_azure_ad_connector",
    "configure_azure_ad_connector",
    "shutdown_azure_ad_connector",
]
