"""
C4 Documentation Generation Agent.

Automated C4 architecture documentation generator.
Analyzes codebase and generates/updates Mermaid diagrams and documentation.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from .base import AgentConfig, AgentResult, AgentStatus, BaseGovernanceAgent

logger = logging.getLogger(__name__)


class C4Level(Enum):
    """C4 model documentation levels."""

    CONTEXT = "context"
    CONTAINER = "container"
    COMPONENT = "component"
    CODE = "code"


@dataclass
class C4Element:
    """An element in the C4 model."""

    name: str
    element_type: str  # person, system, container, component
    description: str
    technology: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    relationships: List[Dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.element_type,
            "description": self.description,
            "technology": self.technology,
            "tags": self.tags,
            "relationships": self.relationships,
        }


@dataclass
class C4Diagram:
    """A C4 diagram with Mermaid representation."""

    title: str
    level: C4Level
    elements: List[C4Element]
    mermaid_code: str
    source_files: List[str]
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "level": self.level.value,
            "element_count": len(self.elements),
            "source_files": self.source_files,
            "last_updated": self.last_updated.isoformat(),
        }


@dataclass
class DocumentationReport:
    """Report on documentation generation."""

    diagrams_generated: List[C4Diagram]
    files_created: List[str]
    files_updated: List[str]
    coverage_gaps: List[str]
    recommendations: List[str]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "diagrams_generated": len(self.diagrams_generated),
            "files_created": self.files_created,
            "files_updated": self.files_updated,
            "coverage_gaps": self.coverage_gaps,
            "recommendations": self.recommendations,
            "timestamp": self.timestamp.isoformat(),
        }


class C4DocsAgent(BaseGovernanceAgent):
    """
    Agent for C4 architecture documentation generation.

    Capabilities:
    - Read existing C4 documentation in docs/architecture/c4
    - Generate/update Mermaid diagrams from code analysis
    - Validate C4 model completeness (Context → Container → Component → Code)
    - Create new documentation for undocumented modules

    Subagents:
    - code-analyzer: Extracts function signatures and dependencies
    - diagram-generator: Creates Mermaid diagram syntax
    """

    # C4 documentation paths
    C4_DOCS_PATH = "docs/architecture/c4"
    C4_LEVELS_REQUIRED = [C4Level.CONTEXT, C4Level.CONTAINER, C4Level.COMPONENT]

    def __init__(self, config: Optional[AgentConfig] = None):
        """Initialize the C4 documentation agent."""
        default_config = AgentConfig(
            allowed_tools=["Read", "Write", "Glob", "Grep", "Task"],
            permission_mode="acceptEdits",  # Allow documentation writes
            agents={
                "code-analyzer": {
                    "description": "Analyzes code to extract structure and dependencies",
                    "prompt": "Analyze the given code files to extract function signatures, class definitions, and dependencies.",
                    "tools": ["Read", "Glob", "Grep"],
                },
                "diagram-generator": {
                    "description": "Generates Mermaid diagrams from structural data",
                    "prompt": "Generate Mermaid diagram code for C4 architecture visualization.",
                    "tools": ["Read"],
                },
            },
        )

        if config:
            default_config.allowed_tools = config.allowed_tools or default_config.allowed_tools
            default_config.permission_mode = config.permission_mode

        super().__init__("c4-docs-agent", default_config)

        self._generated_diagrams: List[C4Diagram] = []

    @property
    def description(self) -> str:
        return (
            "C4 architecture documentation generator for ACGS-2. "
            "Creates and maintains Mermaid diagrams and documentation."
        )

    @property
    def system_prompt(self) -> str:
        return """You are a C4 architecture documentation agent for the ACGS-2 system.

Your role is to generate and maintain C4 model documentation with Mermaid diagrams.

C4 Model Levels:
1. Context - System context showing users and external systems
2. Container - High-level technology containers (services, databases, etc.)
3. Component - Internal components within each container
4. Code - Optional code-level documentation

Documentation Location: docs/architecture/c4/

When generating documentation:
- Analyze existing code structure using Read, Glob, Grep tools
- Extract module boundaries, dependencies, and interfaces
- Generate Mermaid diagrams following C4 conventions
- Create markdown documentation with embedded diagrams
- Validate completeness across all C4 levels

Mermaid C4 Diagram Syntax:
```mermaid
C4Context
    title System Context Diagram
    Person(user, "User", "A user of the system")
    System(system, "System Name", "Description")
    Rel(user, system, "Uses")
```

Output format:
- Generated/updated diagram files
- Coverage analysis (which modules lack documentation)
- Recommendations for improving documentation
- Validation of C4 model completeness

Use the code-analyzer subagent for deep code analysis.
Use the diagram-generator subagent for creating Mermaid syntax.
"""

    async def run(self, prompt: str) -> AgentResult:
        """
        Execute C4 documentation generation.

        Args:
            prompt: Documentation request (e.g., "Generate C4 docs for governance module")

        Returns:
            AgentResult with documentation report
        """
        self.status = AgentStatus.RUNNING
        logger.info(f"Starting C4 documentation generation: {prompt[:100]}...")

        try:
            # Execute pre-tool hooks
            await self._execute_hooks("PreToolUse", {"prompt": prompt})

            # Simulate documentation generation
            report = await self._simulate_doc_generation(prompt)

            # Execute post-tool hooks
            await self._execute_hooks(
                "PostToolUse",
                {
                    "prompt": prompt,
                    "report": report.to_dict(),
                },
            )

            self.status = AgentStatus.COMPLETED

            return AgentResult(
                agent_name=self.name,
                status=AgentStatus.COMPLETED,
                result=self._format_doc_report(report),
                metrics={
                    "diagrams_generated": len(report.diagrams_generated),
                    "files_created": len(report.files_created),
                    "files_updated": len(report.files_updated),
                    "coverage_gaps": len(report.coverage_gaps),
                },
            )

        except Exception as e:
            logger.error(f"C4 documentation generation failed: {e}")
            self.status = AgentStatus.FAILED
            return AgentResult(
                agent_name=self.name,
                status=AgentStatus.FAILED,
                errors=[str(e)],
            )

    async def analyze_module(self, module_path: str) -> List[C4Element]:
        """
        Analyze a module to extract C4 elements.

        Args:
            module_path: Path to the module

        Returns:
            List of C4 elements found
        """
        elements = []

        # In production, would use code-analyzer subagent
        # Simulate extraction
        elements.append(
            C4Element(
                name=module_path.split("/")[-1],
                element_type="component",
                description=f"Component from {module_path}",
                technology="Python",
                tags=["governance", "core"],
                relationships=[],
            )
        )

        return elements

    async def generate_mermaid(
        self,
        level: C4Level,
        elements: List[C4Element],
        title: str,
    ) -> str:
        """
        Generate Mermaid diagram code for C4 elements.

        Args:
            level: C4 level for the diagram
            elements: Elements to include
            title: Diagram title

        Returns:
            Mermaid diagram code
        """
        # Select diagram type based on level
        diagram_type = {
            C4Level.CONTEXT: "C4Context",
            C4Level.CONTAINER: "C4Container",
            C4Level.COMPONENT: "C4Component",
            C4Level.CODE: "classDiagram",
        }[level]

        lines = [
            f"{diagram_type}",
            f"    title {title}",
            "",
        ]

        # Add elements
        for elem in elements:
            elem_func = {
                "person": "Person",
                "system": "System",
                "container": "Container",
                "component": "Component",
            }.get(elem.element_type, "Component")

            elem_id = elem.name.lower().replace(" ", "_").replace("-", "_")
            tech_str = f", {elem.technology}" if elem.technology else ""

            lines.append(
                f'    {elem_func}({elem_id}, "{elem.name}", "{elem.description}"{tech_str})'
            )

        # Add relationships
        for elem in elements:
            elem_id = elem.name.lower().replace(" ", "_").replace("-", "_")
            for rel in elem.relationships:
                target_id = rel["target"].lower().replace(" ", "_").replace("-", "_")
                lines.append(f"    Rel({elem_id}, {target_id}, \"{rel['description']}\")")

        return "\n".join(lines)

    async def validate_c4_completeness(self, docs_path: str) -> List[str]:
        """
        Validate C4 model completeness.

        Args:
            docs_path: Path to C4 documentation

        Returns:
            List of coverage gaps
        """
        gaps = []

        # Check for required levels
        for _level in self.C4_LEVELS_REQUIRED:
            # In production, would scan docs_path for level documentation
            pass

        return gaps

    async def _simulate_doc_generation(self, prompt: str) -> DocumentationReport:
        """Simulate documentation generation for testing."""
        await asyncio.sleep(0.1)

        # Create sample diagram
        elements = [
            C4Element(
                name="Governance Service",
                element_type="container",
                description="Core governance service handling policy validation",
                technology="Python, FastAPI",
                tags=["governance", "api"],
                relationships=[
                    {"target": "OPA", "description": "Validates policies"},
                    {"target": "Database", "description": "Stores governance data"},
                ],
            ),
            C4Element(
                name="OPA",
                element_type="container",
                description="Open Policy Agent for policy enforcement",
                technology="Rego",
                tags=["policy", "external"],
            ),
            C4Element(
                name="Database",
                element_type="container",
                description="PostgreSQL database for persistence",
                technology="PostgreSQL",
                tags=["storage"],
            ),
        ]

        mermaid_code = await self.generate_mermaid(
            C4Level.CONTAINER,
            elements,
            "ACGS-2 Governance Container Diagram",
        )

        diagram = C4Diagram(
            title="ACGS-2 Governance Container Diagram",
            level=C4Level.CONTAINER,
            elements=elements,
            mermaid_code=mermaid_code,
            source_files=[
                "src/core/governance/",
                "src/core/services/",
            ],
        )

        self._generated_diagrams.append(diagram)

        return DocumentationReport(
            diagrams_generated=[diagram],
            files_created=["c4-container-governance.md"],
            files_updated=[],
            coverage_gaps=[
                "Missing: Code-level documentation for dfc.py",
                "Missing: Component diagram for deliberation layer",
            ],
            recommendations=[
                "Generate code-level documentation for governance metrics",
                "Add component diagram showing deliberation workflow",
                "Update context diagram with external regulatory systems",
            ],
        )

    def _format_doc_report(self, report: DocumentationReport) -> str:
        """Format documentation report for display."""
        lines = [
            "# C4 Documentation Report",
            "",
            f"**Generated:** {report.timestamp.strftime('%Y-%m-%d %H:%M UTC')}",
            "",
            "---",
            "",
            "## Summary",
            "",
            f"- Diagrams Generated: {len(report.diagrams_generated)}",
            f"- Files Created: {len(report.files_created)}",
            f"- Files Updated: {len(report.files_updated)}",
            f"- Coverage Gaps: {len(report.coverage_gaps)}",
            "",
        ]

        if report.diagrams_generated:
            lines.extend(["## Generated Diagrams", ""])

            for diagram in report.diagrams_generated:
                lines.extend(
                    [
                        f"### {diagram.title}",
                        "",
                        f"**Level:** {diagram.level.value.title()}",
                        f"**Elements:** {len(diagram.elements)}",
                        "",
                        "```mermaid",
                        diagram.mermaid_code,
                        "```",
                        "",
                    ]
                )

        if report.files_created:
            lines.extend(
                [
                    "## Files Created",
                    "",
                    *[f"- `{f}`" for f in report.files_created],
                    "",
                ]
            )

        if report.files_updated:
            lines.extend(
                [
                    "## Files Updated",
                    "",
                    *[f"- `{f}`" for f in report.files_updated],
                    "",
                ]
            )

        if report.coverage_gaps:
            lines.extend(
                [
                    "## Coverage Gaps",
                    "",
                    *[f"- ⚠️ {gap}" for gap in report.coverage_gaps],
                    "",
                ]
            )

        if report.recommendations:
            lines.extend(
                [
                    "## Recommendations",
                    "",
                    *[f"- {rec}" for rec in report.recommendations],
                ]
            )

        return "\n".join(lines)


async def main():
    """Test the C4 documentation agent."""
    agent = C4DocsAgent()

    await agent.run("Generate C4 container diagram for the governance service")


if __name__ == "__main__":
    asyncio.run(main())
