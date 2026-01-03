"""
Template Service for rendering Jinja2 templates
"""

import logging
import os
from typing import Any, Dict, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger(__name__)


class TemplateService:
    """Manages Jinja2 template rendering."""

    def __init__(self, templates_dir: Optional[str] = None):
        if not templates_dir:
            templates_dir = os.getenv("COMPLIANCE_TEMPLATES_PATH", "src/templates")

        self.env = Environment(
            loader=FileSystemLoader(templates_dir),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        logger.info(f"TemplateService initialized with templates from {templates_dir}")

    def render(self, template_path: str, context: Dict[str, Any]) -> str:
        """
        Render a template with the provided context.

        Args:
            template_path: Path to template file relative to templates_dir
            context: Variables to pass to the template

        Returns:
            Rendered string
        """
        try:
            template = self.env.get_template(template_path)
            return template.render(**context)
        except Exception as e:
            logger.error(f"Failed to render template {template_path}: {e}")
            raise
