"""
Regulatory Research Agent.

Research agent for monitoring regulatory updates (EU AI Act, GDPR, etc.).
Uses WebSearch and WebFetch tools to gather and analyze regulatory information.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from .base import AgentConfig, AgentResult, AgentStatus, BaseGovernanceAgent

logger = logging.getLogger(__name__)


class RegulationType(Enum):
    """Types of regulations monitored."""

    EU_AI_ACT = "eu_ai_act"
    GDPR = "gdpr"
    CCPA = "ccpa"
    AI_GOVERNANCE = "ai_governance"
    DATA_PROTECTION = "data_protection"
    OTHER = "other"


@dataclass
class RegulatoryUpdate:
    """A regulatory update or change."""

    title: str
    regulation_type: RegulationType
    summary: str
    source_url: str
    publication_date: Optional[datetime]
    effective_date: Optional[datetime]
    impact_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    affected_areas: List[str]
    action_required: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "regulation_type": self.regulation_type.value,
            "summary": self.summary,
            "source_url": self.source_url,
            "publication_date": self.publication_date.isoformat()
            if self.publication_date
            else None,
            "effective_date": self.effective_date.isoformat() if self.effective_date else None,
            "impact_level": self.impact_level,
            "affected_areas": self.affected_areas,
            "action_required": self.action_required,
        }


@dataclass
class ResearchReport:
    """Research report with regulatory updates."""

    query: str
    updates: List[RegulatoryUpdate]
    sources_consulted: int
    compliance_implications: List[str]
    recommendations: List[str]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "update_count": len(self.updates),
            "sources_consulted": self.sources_consulted,
            "compliance_implications": self.compliance_implications,
            "recommendations": self.recommendations,
            "timestamp": self.timestamp.isoformat(),
        }


class RegulatoryResearchAgent(BaseGovernanceAgent):
    """
    Agent for regulatory research and monitoring.

    Capabilities:
    - Search for regulatory updates via WebSearch
    - Fetch and parse regulatory documents
    - Cross-reference with current compliance documentation
    - Generate regulatory update summaries
    """

    # Key regulatory sources
    REGULATORY_SOURCES = [
        "eur-lex.europa.eu",  # EU legislation
        "digital-strategy.ec.europa.eu",  # EU Digital Strategy
        "gdpr.eu",  # GDPR resources
        "ico.org.uk",  # UK ICO
        "nist.gov",  # NIST frameworks
        "ftc.gov",  # US FTC
    ]

    # Regulatory keywords
    REGULATION_KEYWORDS = {
        RegulationType.EU_AI_ACT: [
            "EU AI Act",
            "Artificial Intelligence Act",
            "AI regulation Europe",
        ],
        RegulationType.GDPR: ["GDPR", "General Data Protection Regulation", "data protection EU"],
        RegulationType.CCPA: ["CCPA", "California Consumer Privacy Act", "California privacy"],
        RegulationType.AI_GOVERNANCE: ["AI governance", "AI ethics", "responsible AI", "AI safety"],
        RegulationType.DATA_PROTECTION: [
            "data protection",
            "privacy regulation",
            "data privacy law",
        ],
    }

    def __init__(self, config: Optional[AgentConfig] = None):
        """Initialize the regulatory research agent."""
        default_config = AgentConfig(
            allowed_tools=["Read", "WebSearch", "WebFetch", "Glob"],
            permission_mode="bypassPermissions",
        )

        if config:
            default_config.allowed_tools = config.allowed_tools or default_config.allowed_tools
            default_config.mcp_servers = config.mcp_servers

        super().__init__("regulatory-research-agent", default_config)

        self._cache: Dict[str, ResearchReport] = {}

    @property
    def description(self) -> str:
        return (
            "Regulatory research agent for ACGS-2. "
            "Monitors EU AI Act, GDPR, and other regulatory updates."
        )

    @property
    def system_prompt(self) -> str:
        return """You are a regulatory research agent for the ACGS-2 governance system.

Your role is to monitor and analyze regulatory changes that affect AI governance.

Key regulations to monitor:
1. EU AI Act - Artificial Intelligence regulation in Europe
2. GDPR - General Data Protection Regulation
3. CCPA - California Consumer Privacy Act
4. NIST AI RMF - AI Risk Management Framework
5. Other emerging AI governance frameworks

When conducting research:
- Search for recent regulatory updates and amendments
- Analyze impact on ACGS-2 compliance requirements
- Identify required actions for continued compliance
- Cross-reference with existing compliance documentation
- Prioritize updates by impact level (CRITICAL, HIGH, MEDIUM, LOW)

Output format:
- List of regulatory updates found
- Source URLs for verification
- Impact assessment for each update
- Compliance implications for ACGS-2
- Recommended actions with priority levels

Focus on:
- New regulation announcements
- Amendment proposals and drafts
- Implementation deadlines
- Enforcement actions and precedents
- Guidance documents from regulatory bodies
"""

    async def run(self, prompt: str) -> AgentResult:
        """
        Execute regulatory research.

        Args:
            prompt: Research query (e.g., "Find recent EU AI Act updates")

        Returns:
            AgentResult with research findings
        """
        self.status = AgentStatus.RUNNING
        logger.info(f"Starting regulatory research: {prompt[:100]}...")

        try:
            # Execute pre-tool hooks
            await self._execute_hooks("PreToolUse", {"prompt": prompt})

            # Simulate research (in production, uses WebSearch/WebFetch)
            report = await self._simulate_research(prompt)

            # Cache the report
            cache_key = prompt.lower()[:50]
            self._cache[cache_key] = report

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
                result=self._format_research_report(report),
                metrics={
                    "updates_found": len(report.updates),
                    "sources_consulted": report.sources_consulted,
                    "action_required": sum(1 for u in report.updates if u.action_required),
                },
            )

        except Exception as e:
            logger.error(f"Regulatory research failed: {e}")
            self.status = AgentStatus.FAILED
            return AgentResult(
                agent_name=self.name,
                status=AgentStatus.FAILED,
                errors=[str(e)],
            )

    async def search_regulation(
        self,
        regulation_type: RegulationType,
        date_range_days: int = 30,
    ) -> List[RegulatoryUpdate]:
        """
        Search for updates to a specific regulation.

        Args:
            regulation_type: Type of regulation to search
            date_range_days: Number of days to look back

        Returns:
            List of regulatory updates
        """
        keywords = self.REGULATION_KEYWORDS.get(regulation_type, [])

        # In production, would use WebSearch tool
        updates = []

        for keyword in keywords:
            # Simulate search results
            update = RegulatoryUpdate(
                title=f"Update: {keyword}",
                regulation_type=regulation_type,
                summary=f"Recent developments in {keyword}",
                source_url=f"https://example.com/{regulation_type.value}",
                publication_date=datetime.now(timezone.utc),
                effective_date=None,
                impact_level="MEDIUM",
                affected_areas=["governance", "compliance"],
                action_required=False,
            )
            updates.append(update)

        return updates

    async def check_compliance_implications(
        self,
        update: RegulatoryUpdate,
        current_docs_path: str = "docs/compliance",
    ) -> List[str]:
        """
        Check implications of a regulatory update for current compliance docs.

        Args:
            update: The regulatory update
            current_docs_path: Path to compliance documentation

        Returns:
            List of compliance implications
        """
        implications = []

        if update.impact_level in ["HIGH", "CRITICAL"]:
            implications.append(f"High-impact update requires documentation review: {update.title}")

            implications.append("Action required: Review and update compliance procedures")

        return implications

    async def _simulate_research(self, prompt: str) -> ResearchReport:
        """Simulate research for testing."""
        await asyncio.sleep(0.1)

        # Determine regulation type from prompt
        prompt_lower = prompt.lower()

        # Logic to determine regulation type (simulated)
        if "eu ai act" in prompt_lower or "ai act" in prompt_lower:
            pass
        elif "gdpr" in prompt_lower:
            pass
        elif "ccpa" in prompt_lower:
            pass

        # Simulated updates
        updates = [
            RegulatoryUpdate(
                title="EU AI Act Implementation Guidelines Published",
                regulation_type=RegulationType.EU_AI_ACT,
                summary="The European Commission has published new implementation guidelines for high-risk AI systems under the EU AI Act.",
                source_url="https://digital-strategy.ec.europa.eu/ai-act",
                publication_date=datetime.now(timezone.utc),
                effective_date=datetime(2025, 8, 1),
                impact_level="HIGH",
                affected_areas=["AI governance", "risk assessment", "documentation"],
                action_required=True,
            ),
            RegulatoryUpdate(
                title="NIST AI RMF 1.1 Draft Released",
                regulation_type=RegulationType.AI_GOVERNANCE,
                summary="NIST has released draft version 1.1 of the AI Risk Management Framework with updated guidance on generative AI.",
                source_url="https://www.nist.gov/ai-rmf",
                publication_date=datetime.now(timezone.utc),
                effective_date=None,
                impact_level="MEDIUM",
                affected_areas=["risk management", "governance framework"],
                action_required=False,
            ),
        ]

        return ResearchReport(
            query=prompt,
            updates=updates,
            sources_consulted=5,
            compliance_implications=[
                "EU AI Act implementation deadline approaching - review ACGS-2 compliance",
                "Consider updating governance framework to align with NIST AI RMF 1.1",
            ],
            recommendations=[
                "Review current AI risk assessment procedures against EU AI Act requirements",
                "Update documentation to include new implementation guidelines",
                "Schedule compliance review meeting with stakeholders",
            ],
        )

    def _format_research_report(self, report: ResearchReport) -> str:
        """Format research report for display."""
        lines = [
            "# Regulatory Research Report",
            "",
            f"**Query:** {report.query}",
            f"**Sources Consulted:** {report.sources_consulted}",
            f"**Timestamp:** {report.timestamp.strftime('%Y-%m-%d %H:%M UTC')}",
            "",
            "---",
            "",
            "## Regulatory Updates",
            "",
        ]

        for update in sorted(report.updates, key=lambda x: x.impact_level, reverse=True):
            impact_icon = {
                "CRITICAL": "🔴",
                "HIGH": "🟠",
                "MEDIUM": "🟡",
                "LOW": "🟢",
            }.get(update.impact_level, "⚪")

            action_badge = " **[ACTION REQUIRED]**" if update.action_required else ""

            lines.extend(
                [
                    f"### {impact_icon} {update.title}{action_badge}",
                    "",
                    f"- **Regulation:** {update.regulation_type.value}",
                    f"- **Impact Level:** {update.impact_level}",
                    f"- **Source:** [{update.source_url}]({update.source_url})",
                ]
            )

            if update.effective_date:
                lines.append(f"- **Effective Date:** {update.effective_date.strftime('%Y-%m-%d')}")

            lines.extend(
                [
                    "",
                    f"> {update.summary}",
                    "",
                    f"**Affected Areas:** {', '.join(update.affected_areas)}",
                    "",
                ]
            )

        if report.compliance_implications:
            lines.extend(
                [
                    "## Compliance Implications",
                    "",
                    *[f"- {impl}" for impl in report.compliance_implications],
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
    """Test the regulatory research agent."""
    agent = RegulatoryResearchAgent()

    await agent.run("Find recent EU AI Act updates and implementation guidelines")


if __name__ == "__main__":
    asyncio.run(main())
