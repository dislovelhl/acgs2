"""
Template Library Service
Manages pre-built constitutional governance templates.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class TemplateLibraryService:
    """Service for managing the pre-built template library"""

    def __init__(self, templates_dir: Optional[str] = None):
        if not templates_dir:
            # Default to relative path from this file
            base_dir = Path(__file__).parent.parent
            templates_dir = str(base_dir / "templates")

        self.templates_dir = Path(templates_dir)

    def list_templates(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all available templates, optionally filtered by category"""
        templates = []

        search_path = self.templates_dir
        if category:
            search_path = self.templates_dir / category

        if not search_path.exists():
            return []

        # Recursively find all .rego files
        for rego_file in search_path.glob("**/*.rego"):
            rel_path = rego_file.relative_to(self.templates_dir)
            cat = rel_path.parts[0] if len(rel_path.parts) > 1 else "general"

            templates.append(
                {
                    "id": str(rel_path),
                    "name": rego_file.stem.replace("_", " ").title(),
                    "category": cat,
                    "path": str(rel_path),
                }
            )

        return templates

    def get_template_content(self, template_id: str) -> Optional[str]:
        """Fetch the raw content of a template"""
        file_path = self.templates_dir / template_id
        if not file_path.exists() or not file_path.is_file():
            return None

        try:
            with open(file_path, "r") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to read template {template_id}: {e}")
            return None

    def get_template_metadata(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Fetch metadata for a template"""
        file_path = self.templates_dir / template_id
        if not file_path.exists():
            return None

        return {
            "id": template_id,
            "name": file_path.stem.replace("_", " ").title(),
            "category": (
                Path(template_id).parts[0] if len(Path(template_id).parts) > 1 else "general"
            ),
            "size": file_path.stat().st_size,
            "last_modified": file_path.stat().st_mtime,
        }
