"""
ACGS-2 Workflow Template Engine
Constitutional Hash: cdd01ef066bc6cf2

Loads YAML workflow definitions and instantiates workflows.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

import yaml

from ..base.workflow import BaseWorkflow

try:
    from shared.constants import CONSTITUTIONAL_HASH
except ImportError:
    CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


logger = logging.getLogger(__name__)


@dataclass
class WorkflowTemplate:
    """
    Parsed workflow template.

    Attributes:
        name: Template name
        version: Template version
        description: Template description
        constitutional_hash: Required constitutional hash
        workflow_type: Type of workflow (saga, dag, etc.)
        steps: Step definitions
        config: Workflow configuration
    """

    name: str
    version: str
    description: str
    constitutional_hash: str
    workflow_type: str
    steps: List[Dict[str, Any]]
    config: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowTemplate":
        """Create template from dictionary."""
        return cls(
            name=data.get("name", "unnamed"),
            version=data.get("version", "1.0.0"),
            description=data.get("description", ""),
            constitutional_hash=data.get("constitutional_hash", CONSTITUTIONAL_HASH),
            workflow_type=data.get("workflow_type", "sequential"),
            steps=data.get("steps", []),
            config=data.get("config", {}),
            metadata=data.get("metadata", {}),
        )

    def validate(self) -> List[str]:
        """
        Validate template.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        if not self.name:
            errors.append("Template name is required")

        if self.constitutional_hash != CONSTITUTIONAL_HASH:
            errors.append(
                f"Constitutional hash mismatch: expected {CONSTITUTIONAL_HASH}, "
                f"got {self.constitutional_hash}"
            )

        if not self.steps:
            errors.append("At least one step is required")

        for i, step in enumerate(self.steps):
            if "name" not in step:
                errors.append(f"Step {i}: name is required")
            if "action" not in step and "execute" not in step:
                errors.append(f"Step {i}: action or execute is required")

        return errors


class TemplateEngine:
    """
    Workflow template engine.

    Loads YAML templates and creates workflow instances.

    Example:
        engine = TemplateEngine()
        engine.register_action("validate_hash", validate_hash_fn)

        template = engine.load("simple_approval.yaml")
        workflow = engine.create_workflow(template)
        result = await workflow.run(input)
    """

    def __init__(
        self,
        template_dir: Optional[Path] = None,
        constitutional_hash: str = CONSTITUTIONAL_HASH,
    ):
        """
        Initialize template engine.

        Args:
            template_dir: Directory containing templates
            constitutional_hash: Expected constitutional hash
        """
        self.template_dir = template_dir or Path(__file__).parent
        self.constitutional_hash = constitutional_hash
        self._actions: Dict[str, callable] = {}
        self._workflow_types: Dict[str, Type[BaseWorkflow]] = {}
        self._templates: Dict[str, WorkflowTemplate] = {}

    def register_action(self, name: str, action: callable) -> None:
        """
        Register an action function.

        Args:
            name: Action name used in templates
            action: Async function to execute
        """
        self._actions[name] = action
        logger.debug(f"Registered action: {name}")

    def register_workflow_type(self, name: str, workflow_class: Type[BaseWorkflow]) -> None:
        """
        Register a workflow type.

        Args:
            name: Type name used in templates
            workflow_class: Workflow class to instantiate
        """
        self._workflow_types[name] = workflow_class
        logger.debug(f"Registered workflow type: {name}")

    def load(self, template_path: str) -> WorkflowTemplate:
        """
        Load a template from file.

        Args:
            template_path: Path to template file (relative or absolute)

        Returns:
            Parsed WorkflowTemplate

        Raises:
            FileNotFoundError: If template not found
            ValueError: If template is invalid
        """
        # Check if cached
        if template_path in self._templates:
            return self._templates[template_path]

        # Resolve path
        if Path(template_path).is_absolute():
            full_path = Path(template_path)
        else:
            full_path = self.template_dir / template_path

        if not full_path.exists():
            raise FileNotFoundError(f"Template not found: {full_path}")

        # Load YAML
        with open(full_path, "r") as f:
            data = yaml.safe_load(f)

        # Parse template
        template = WorkflowTemplate.from_dict(data)

        # Validate
        errors = template.validate()
        if errors:
            raise ValueError(f"Template validation failed: {errors}")

        # Cache
        self._templates[template_path] = template

        logger.info(f"Loaded template: {template.name} v{template.version}")
        return template

    def load_from_string(self, yaml_content: str) -> WorkflowTemplate:
        """
        Load a template from YAML string.

        Args:
            yaml_content: YAML template content

        Returns:
            Parsed WorkflowTemplate
        """
        data = yaml.safe_load(yaml_content)
        template = WorkflowTemplate.from_dict(data)

        errors = template.validate()
        if errors:
            raise ValueError(f"Template validation failed: {errors}")

        return template

    def get_action(self, name: str) -> Optional[callable]:
        """
        Get registered action by name.

        Args:
            name: Action name

        Returns:
            Action function or None
        """
        return self._actions.get(name)

    def list_templates(self) -> List[str]:
        """
        List available templates in template directory.

        Returns:
            List of template filenames
        """
        templates = []
        if self.template_dir.exists():
            for path in self.template_dir.glob("*.yaml"):
                templates.append(path.name)
            for path in self.template_dir.glob("*.yml"):
                templates.append(path.name)
        return sorted(templates)


__all__ = [
    "WorkflowTemplate",
    "TemplateEngine",
]
