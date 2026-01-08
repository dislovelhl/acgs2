import os
import re
from pathlib import Path


def extract_rules_from_rego(rego_content):
    """Simple regex-based extraction of rules from Rego files."""
    # Match rule definitions like 'allow { ... }' or 'deny[msg] { ... }'
    pattern = re.compile(r"^(\w+(?:\[\w+\])?)\s*\{", re.MULTILINE)
    matches = pattern.findall(rego_content)
    return matches


def generate_markdown_table(policies):
    """Generates a Markdown table of policies and their rules."""
    md = "# Active Governance Rules (OPA/Rego)\n\n"
    md += "| Policy File | Rules Detected | Description |\n"
    md += "| :--- | :--- | :--- |\n"

    for file_path, rules in policies.items():
        rules_str = ", ".join([f"`{r}`" for r in rules])
        description = "Constitutional enforcement rule"
        md += f"| {file_path} | {rules_str} | {description} |\n"

    return md


def main():
    policy_dir = Path("/home/dislove/document/acgs2/acgs2-core/policies/rego")
    output_file = Path("/home/dislove/document/acgs2/docs/summaries/rego_rules.md")

    policies = {}

    if not policy_dir.exists():
        return

    for rego_file in policy_dir.glob("**/*.rego"):
        with open(rego_file, "r") as f:
            content = f.read()
            rules = extract_rules_from_rego(content)
            if rules:
                relative_path = rego_file.relative_to(policy_dir.parent.parent)
                policies[str(relative_path)] = rules

    if policies:
        os.makedirs(output_file.parent, exist_ok=True)
        with open(output_file, "w") as f:
            f.write(generate_markdown_table(policies))
    else:
        pass


if __name__ == "__main__":
    main()
