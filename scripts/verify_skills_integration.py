import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent.absolute()))

from src.agents.base import AgentConfig, BaseGovernanceAgent

logging.basicConfig(level=logging.INFO)

class TestSkillAgent(BaseGovernanceAgent):
    @property
    def description(self) -> str:
        return "Agent for testing skill integration."

    @property
    def system_prompt(self) -> str:
        return "You are a test agent."

async def test_skill_integration():
    print("\n--- Testing Skill Integration ---\n")

    # Initialize agent with 'pdf' skill
    config = AgentConfig(skills=["pdf"])
    agent = TestSkillAgent("pdf-test-agent", config)

    # 1. Verify skills are loaded
    print(f"Loaded skills in manager: {[s.metadata.name for s in agent.skill_manager.get_all_skills()]}")

    # 2. Verify effective system prompt
    effective_prompt = agent.get_effective_system_prompt()
    print("\nEffective System Prompt (Truncated):\n")
    print(f"{effective_prompt[:500]}...")

    if "### Skill: pdf" in effective_prompt and "PDF Processing Guide" in effective_prompt:
        print("\n✅ System prompt successfully augmented with PDF skill instructions.")
    else:
        print("\n❌ System prompt augmentation failed.")
        sys.exit(1)

    # 3. Verify skill paths
    skill_paths = agent.skill_manager.get_skill_paths(agent.config.skills)
    print(f"\nSkill Paths: {skill_paths}")
    for path in skill_paths:
        if Path(path).exists():
            print(f"✅ Skill path exists: {path}")
        else:
            print(f"❌ Skill path does not exist: {path}")
            sys.exit(1)

    print("\n--- Skill Integration Test Passed! ---\n")

if __name__ == "__main__":
    asyncio.run(test_skill_integration())
