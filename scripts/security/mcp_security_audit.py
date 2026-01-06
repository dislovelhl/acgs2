#!/usr/bin/env python3
"""
ACGS-2 MCP Server Security Audit
================================

Audits third-party MCP server configurations in mcp.json for security compliance.

Checks performed:
1. Protocol validation (HTTPS/SSL enforcement)
2. Certificate validation requirements
3. Secure credential handling
4. Network security best practices
5. Configuration consistency

Constitutional Hash: cdd01ef066bc6cf2
"""

import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlparse

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class MCPSecurityAuditor:
    """Audits MCP server configurations for security compliance."""

    def __init__(self, mcp_config_path: str, env_file_path: str = None):
        self.mcp_config_path = Path(mcp_config_path)
        self.env_file_path = Path(env_file_path) if env_file_path else None
        self.findings = []
        self.warnings = []
        self.errors = []

    def load_config(self) -> Dict[str, Any]:
        """Load MCP configuration from JSON file."""
        try:
            with open(self.mcp_config_path, "r") as f:
                return json.load(f)
        except Exception as e:
            self.errors.append(f"Failed to load MCP config: {e}")
            return {}

    def load_env_vars(self) -> Dict[str, str]:
        """Load environment variables from .env file."""
        env_vars = {}
        if self.env_file_path and self.env_file_path.exists():
            try:
                with open(self.env_file_path, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            if "=" in line:
                                key, value = line.split("=", 1)
                                env_vars[key] = value
            except Exception as e:
                self.warnings.append(f"Failed to load env file: {e}")
        return env_vars

    def audit_url_security(
        self, server_name: str, config: Dict[str, Any], env_vars: Dict[str, str]
    ) -> None:
        """Audit URL-based security configurations."""
        # Check direct URL configurations
        if "url" in config:
            url = config["url"]
            self._audit_url(server_name, url, "direct URL")

        # Check command-based configurations with environment variables
        if "args" in config:
            for arg in config["args"]:
                # Check for environment variable usage
                if arg.startswith("${") and arg.endswith("}"):
                    env_var = arg[2:-1]  # Remove ${}
                    if env_var in env_vars:
                        value = env_vars[env_var]
                        if self._is_url_like(value):
                            self._audit_url(server_name, value, f"env var {env_var}")

    def _is_url_like(self, value: str) -> bool:
        """Check if a string looks like a URL."""
        return value.startswith(("http://", "https://", "redis://", "rediss://", "postgresql://"))

    def _audit_url(self, server_name: str, url: str, context: str) -> None:
        """Audit a single URL for security issues."""
        parsed = urlparse(url)

        # Check protocol security
        if parsed.scheme in ["http", "redis", "postgresql"]:
            if parsed.scheme == "http":
                self.findings.append(
                    {
                        "severity": "HIGH",
                        "server": server_name,
                        "issue": f"Insecure protocol ({parsed.scheme}) in {context}",
                        "url": url,
                        "recommendation": f"Use HTTPS instead of HTTP for {context}",
                    }
                )
            elif parsed.scheme in ["redis", "postgresql"]:
                self.findings.append(
                    {
                        "severity": "HIGH",
                        "server": server_name,
                        "issue": f"Insecure protocol ({parsed.scheme}) in {context} - no SSL/TLS",
                        "url": url,
                        "recommendation": f"Use {parsed.scheme}s:// (with SSL/TLS) instead of {parsed.scheme}:// for {context}",
                    }
                )

        # Check for localhost/development URLs in production contexts
        if parsed.hostname in ["localhost", "127.0.0.1"] and os.getenv("ACGS_ENV") != "development":
            self.warnings.append(
                {
                    "server": server_name,
                    "issue": f"Localhost URL in non-development environment: {url}",
                    "recommendation": "Use production hostnames in production environments",
                }
            )

    def audit_security_config(self, server_name: str, config: Dict[str, Any]) -> None:
        """Audit security-related configuration options."""
        security_config = config.get("security", {})

        # Check HTTPS enforcement
        if "force_https" in security_config:
            if not security_config["force_https"]:
                self.findings.append(
                    {
                        "severity": "MEDIUM",
                        "server": server_name,
                        "issue": "HTTPS enforcement disabled",
                        "recommendation": "Enable force_https for secure communications",
                    }
                )

        # Check certificate validation
        if "certificate_validation" in security_config:
            if not security_config["certificate_validation"]:
                self.findings.append(
                    {
                        "severity": "HIGH",
                        "server": server_name,
                        "issue": "Certificate validation disabled",
                        "recommendation": "Enable certificate_validation for secure communications",
                    }
                )

    def audit_credentials(self, server_name: str, config: Dict[str, Any]) -> None:
        """Audit credential handling security."""
        # Check for hardcoded credentials
        args = config.get("args", [])
        for arg in args:
            # Look for potential credential patterns
            if re.search(r"password|secret|key|token", arg.lower(), re.IGNORECASE):
                if not arg.startswith("${"):  # Not an environment variable
                    self.findings.append(
                        {
                            "severity": "CRITICAL",
                            "server": server_name,
                            "issue": "Potential hardcoded credentials in command args",
                            "value": arg,
                            "recommendation": "Use environment variables for credentials",
                        }
                    )

        # Check headers for sensitive data
        headers = config.get("headers", {})
        for key, value in headers.items():
            if key.lower() in ["authorization", "api-key", "token"]:
                if not value.startswith("${"):  # Not an environment variable
                    self.findings.append(
                        {
                            "severity": "CRITICAL",
                            "server": server_name,
                            "issue": f"Hardcoded {key} in headers",
                            "recommendation": "Use environment variables for sensitive header values",
                        }
                    )

    def run_audit(self) -> Dict[str, Any]:
        """Run the complete security audit."""
        logger.info(f"Starting MCP security audit for {self.mcp_config_path}")

        config = self.load_config()
        env_vars = self.load_env_vars()

        if not config:
            return {"errors": self.errors}

        mcp_servers = config.get("mcpServers", {})

        for server_name, server_config in mcp_servers.items():
            logger.info(f"Auditing server: {server_name}")

            # Audit URL security
            self.audit_url_security(server_name, server_config, env_vars)

            # Audit security configuration
            self.audit_security_config(server_name, server_config)

            # Audit credential handling
            self.audit_credentials(server_name, server_config)

        # Generate report
        return {
            "summary": {
                "total_servers": len(mcp_servers),
                "findings_count": len(self.findings),
                "warnings_count": len(self.warnings),
                "errors_count": len(self.errors),
            },
            "findings": self.findings,
            "warnings": self.warnings,
            "errors": self.errors,
            "recommendations": self._generate_recommendations(),
        }

    def _generate_recommendations(self) -> List[str]:
        """Generate security recommendations based on findings."""
        recommendations = []

        if any(f["severity"] == "CRITICAL" for f in self.findings):
            recommendations.append(
                "IMMEDIATE: Address critical security findings (hardcoded credentials)"
            )

        if any(f["issue"].startswith("Insecure protocol") for f in self.findings):
            recommendations.append("HIGH PRIORITY: Enable SSL/TLS for all external connections")
            recommendations.append(
                "Update REDIS_URL and POSTGRES_URL to use secure protocols (rediss://, postgresqls://)"
            )

        if any("localhost" in str(f.get("issue", "")) for f in self.warnings):
            recommendations.append(
                "MEDIUM: Use production hostnames instead of localhost in production"
            )

        recommendations.extend(
            [
                "Regularly rotate credentials and API keys",
                "Implement certificate pinning for critical connections",
                "Enable comprehensive logging and monitoring",
                "Regular security audits of MCP configurations",
            ]
        )

        return recommendations

    def print_report(self, results: Dict[str, Any]) -> None:
        """Print the audit report in a human-readable format."""
        print("\n" + "=" * 80)
        print("🔒 ACGS-2 MCP Server Security Audit Report")
        print("=" * 80)

        summary = results.get("summary", {})
        print("\n📊 Summary:")
        print(f"   Total MCP Servers: {summary.get('total_servers', 0)}")
        print(f"   Security Findings: {summary.get('findings_count', 0)}")
        print(f"   Warnings: {summary.get('warnings_count', 0)}")
        print(f"   Errors: {summary.get('errors_count', 0)}")

        if results.get("errors"):
            print("\n❌ Errors:")
            for error in results["errors"]:
                print(f"   - {error}")

        if results.get("findings"):
            print("\n🚨 Security Findings:")
            severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
            sorted_findings = sorted(
                results["findings"], key=lambda x: severity_order.get(x.get("severity", "LOW"), 99)
            )

            for finding in sorted_findings:
                severity = finding.get("severity", "UNKNOWN")
                server = finding.get("server", "unknown")
                issue = finding.get("issue", "Unknown issue")
                recommendation = finding.get("recommendation", "No recommendation")

                print(f"   [{severity}] {server}: {issue}")
                print(f"       💡 {recommendation}")

        if results.get("warnings"):
            print("\n⚠️  Warnings:")
            for warning in results["warnings"]:
                server = warning.get("server", "unknown")
                issue = warning.get("issue", "Unknown issue")
                recommendation = warning.get("recommendation", "No recommendation")

                print(f"   [{server}] {issue}")
                print(f"       💡 {recommendation}")

        if results.get("recommendations"):
            print("\n✅ Recommendations:")
            for rec in results["recommendations"]:
                print(f"   - {rec}")

        print(f"\n{'='*80}")


def main():
    """Main entry point for the security audit."""
    # Default paths
    mcp_config = "/home/dislove/.cursor/mcp.json"
    env_file = "/home/dislove/document/acgs2/.env.dev"

    # Check if custom paths provided
    if len(sys.argv) > 1:
        mcp_config = sys.argv[1]
    if len(sys.argv) > 2:
        env_file = sys.argv[2]

    auditor = MCPSecurityAuditor(mcp_config, env_file)
    results = auditor.run_audit()
    auditor.print_report(results)

    # Exit with error code if critical findings found
    if any(f.get("severity") == "CRITICAL" for f in results.get("findings", [])):
        sys.exit(1)


if __name__ == "__main__":
    main()
