"""
ACGS-2 Enterprise SSO Service
Constitutional Hash: cdd01ef066bc6cf2

Enterprise Single Sign-On integration supporting:
- SAML 2.0 Service Provider (SP)
- OpenID Connect (OIDC) Relying Party (RP)
- Just-In-Time (JIT) user provisioning
- IdP group to MACI role mapping

Supported Identity Providers:
- Okta
- Azure Active Directory
- Google Workspace
- Custom SAML/OIDC IdPs
"""

from .config import IdPConfig, SSOConfig
from .jit_provisioner import JITProvisioner
from .models import IdPType, SSOProtocol, SSOSession, SSOUser
from .oidc_provider import OIDCRelyingParty
from .role_mapper import RoleMapper
from .saml_provider import SAMLServiceProvider
from .session_manager import SSOSessionManager

__all__ = [
    # Configuration
    "SSOConfig",
    "IdPConfig",
    # Models
    "SSOUser",
    "SSOSession",
    "IdPType",
    "SSOProtocol",
    # Providers
    "SAMLServiceProvider",
    "OIDCRelyingParty",
    # Services
    "JITProvisioner",
    "RoleMapper",
    "SSOSessionManager",
]
