"""
Base Skill Infrastructure for ACGS-2.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class SkillMetadata:
    """Metadata for a skill, parsed from SKILL.md frontmatter."""

    name: str
    description: str
    license: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


class BaseSkill:
    """
    Representation of a modular skill.
    """

    def __init__(self, skill_path: Path):
        self.path = skill_path
        self.metadata: Optional[SkillMetadata] = None
        self.instructions: str = ""
        self._load()

    def _load(self):
        """Load SKILL.md content and metadata."""
        skill_md_path = self.path / "SKILL.md"
        if not skill_md_path.exists():
            raise FileNotFoundError(f"SKILL.md not found in {self.path}")

        content = skill_md_path.read_text()

        # Simple frontmatter parser
        if content.startswith("---"):
            _, frontmatter_str, instructions = content.split("---", 2)
            self.instructions = instructions.strip()

            # Parse YAML-like frontmatter
            meta_dict = {}
            for line in frontmatter_str.strip().split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    meta_dict[key.strip()] = value.strip()

            self.metadata = SkillMetadata(
                name=meta_dict.get("name", self.path.name),
                description=meta_dict.get("description", ""),
                license=meta_dict.get("license"),
                extra=meta_dict
            )
        else:
            self.instructions = content
            self.metadata = SkillMetadata(
                name=self.path.name,
                description="No description provided"
            )

    def get_prompt_augmentation(self) -> str:
        """Return instructions to be added to the agent's system prompt."""
        return f"### Skill: {self.metadata.name}\n\n{self.instructions}\n"

    def get_assets_path(self) -> Path:
        """Return the path to the skill's assets (scripts, etc.)."""
        return self.path
