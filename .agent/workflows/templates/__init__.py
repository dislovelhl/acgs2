"""
ACGS-2 Workflow Templates
Constitutional Hash: cdd01ef066bc6cf2

YAML-based declarative workflow definitions:
- Template engine for loading and instantiating workflows
- Pre-built templates for common governance patterns
"""

from .engine import TemplateEngine, WorkflowTemplate

__all__ = [
    "TemplateEngine",
    "WorkflowTemplate",
]
