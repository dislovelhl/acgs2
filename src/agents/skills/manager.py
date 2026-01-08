"""
Skill Manager for ACGS-2.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional

from .base import BaseSkill

logger = logging.getLogger(__name__)

class SkillManager:
    """
    Registry and loader for agent skills.
    """

    def __init__(self, repo_path: Optional[str] = None):
        if repo_path:
            self.repo_path = Path(repo_path)
        else:
            # Default path relative to this file
            self.repo_path = Path(__file__).parent / "repo"

        self._skills: Dict[str, BaseSkill] = {}
        self._load_available_skills()

    def _load_available_skills(self):
        """Discover and load all skills in the repo."""
        if not self.repo_path.exists():
            logger.warning(f"Skill repository path {self.repo_path} does not exist.")
            return

        for skill_dir in self.repo_path.iterdir():
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                try:
                    skill = BaseSkill(skill_dir)
                    self._skills[skill.metadata.name] = skill
                    logger.info(f"Loaded skill: {skill.metadata.name}")
                except Exception as e:
                    logger.error(f"Failed to load skill from {skill_dir}: {e}")

    def get_skill(self, name: str) -> Optional[BaseSkill]:
        """Get a skill by name."""
        return self._skills.get(name)

    def get_all_skills(self) -> List[BaseSkill]:
        """Get all loaded skills."""
        return list(self._skills.values())

    def augment_prompt(self, system_prompt: str, skill_names: List[str]) -> str:
        """
        Augment a system prompt with instructions from specified skills.
        """
        augmentations = []
        for name in skill_names:
            skill = self.get_skill(name)
            if skill:
                augmentations.append(skill.get_prompt_augmentation())
            else:
                logger.warning(f"Skill '{name}' requested but not found.")

        if not augmentations:
            return system_prompt

        skill_section = "\n## Available Specialized Skills\n\n"
        skill_section += "You have access to the following specialized toolkits. Follow their guides strictly:\n\n"
        skill_section += "\n".join(augmentations)

        return f"{system_prompt}\n\n{skill_section}"

    def get_skill_paths(self, skill_names: List[str]) -> List[str]:
        """Return absolute paths to selected skill directories."""
        paths = []
        for name in skill_names:
            skill = self.get_skill(name)
            if skill:
                paths.append(str(skill.path.absolute()))
        return paths
