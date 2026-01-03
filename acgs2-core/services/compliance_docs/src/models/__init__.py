"""
Pydantic models for compliance data structures
"""

from .euaiact import (
    EUAIActComplianceChecklist,
    EUAIActComplianceFinding,
    EUAIActConformityDeclaration,
    EUAIActHumanOversight,
    EUAIActQuarterlyReport,
    EUAIActRiskAssessment,
)
from .gdpr import (
    GDPRArticle30Record,
    GDPRComplianceReport,
    GDPRDataProtectionImpactAssessment,
    GDPRProcessingActivity,
)
from .iso27001 import (
    ISO27001ComplianceReport,
    ISO27001Control,
    ISO27001Evidence,
    ISO27001StatementOfApplicability,
)
from .soc2 import (
    SOC2ComplianceReport,
    SOC2ControlMapping,
    SOC2Evidence,
    SOC2ReportMetadata,
)

__all__ = [
    # SOC 2 models
    "SOC2ControlMapping",
    "SOC2Evidence",
    "SOC2ReportMetadata",
    "SOC2ComplianceReport",
    # ISO 27001 models
    "ISO27001Control",
    "ISO27001Evidence",
    "ISO27001StatementOfApplicability",
    "ISO27001ComplianceReport",
    # GDPR models
    "GDPRProcessingActivity",
    "GDPRArticle30Record",
    "GDPRDataProtectionImpactAssessment",
    "GDPRComplianceReport",
    # EU AI Act models
    "EUAIActComplianceFinding",
    "EUAIActComplianceChecklist",
    "EUAIActRiskAssessment",
    "EUAIActHumanOversight",
    "EUAIActQuarterlyReport",
    "EUAIActConformityDeclaration",
]
