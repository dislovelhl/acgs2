#!/usr/bin/env python3
import logging
import re
import sys
from pathlib import Path

# Constitutional Hash: cdd01ef066bc6cf2


def get_version():
    version_file = Path(__file__).parent.parent / "VERSION"
    if not version_file.exists():
        logging.info("VERSION file not found.")
        return None
    return version_file.read_text().strip()


def update_version_in_files(version):
    root_dir = Path(__file__).parent.parent
    files_to_update = [
        "README.md",
        "README.en.md",
        "PROJECT_INDEX.md",
        "docs/api_reference.md",
        "enhanced_agent_bus/README.md",
    ]

    # Patterns to match:
    # 1. **Version**: 2.2.0
    # 2. **Version:** 2.2.0
    # 3. (v2.2.0)

    patterns = [
        (re.compile(r"(\*\*Version\*\*[:\s]+)[\d\.]+"), r"\g<1>" + version),
        (re.compile(r"(\*\*Version:\*\*[:\s]+)[\d\.]+"), r"\g<1>" + version),
        (re.compile(r"\(v[\d\.]+\)"), f"(v{version})"),
    ]

    for file_path in files_to_update:
        full_path = root_dir / file_path
        if not full_path.exists():
            logging.info(f"File not found: {file_path}")
            continue

        content = full_path.read_text(encoding="utf-8")
        new_content = content

        for pattern, replacement in patterns:
            new_content = pattern.sub(replacement, new_content)

        if new_content != content:
            full_path.write_text(new_content, encoding="utf-8")
            logging.info(f"Updated version in {file_path} to {version}")
        else:
            logging.info(f"No version string found or already up to date in {file_path}")


if __name__ == "__main__":
    version = get_version()
    if version:
        update_version_in_files(version)
        sys.exit(0)
    sys.exit(1)
