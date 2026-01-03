#!/usr/bin/env python3
import logging
import re
import sys
from pathlib import Path

# Constitutional Hash: cdd01ef066bc6cf2


def find_markdown_files(root_dir):
    return list(Path(root_dir).rglob("*.md"))


def extract_links(content):
    # Matches [text](link) but not ![alt](image)
    # Also handles anchors like [text](#anchor)
    links = re.findall(r"(?<!\!)\[.*?\]\((.*?)\)", content)
    return links


def check_links():
    root_dir = Path(__file__).parent.parent
    md_files = find_markdown_files(root_dir)

    errors = []

    for md_file in md_files:
        # Skip node_modules or other common ignored dirs if they exist
        if "node_modules" in str(md_file) or ".git" in str(md_file):
            continue

        with open(md_file, "r", encoding="utf-8") as f:
            content = f.read()

        links = extract_links(content)

        for link in links:
            # Skip external links
            if link.startswith(("http://", "https://", "mailto:", "tel:")):
                continue

            # Handle anchors
            anchor = ""
            if "#" in link:
                link, anchor = link.split("#", 1)

            if not link:
                # It's just an anchor in the same file
                # For now, we just assume internal anchors are valid or skip them
                # as verifying anchors requires parsing the target file's headers
                continue

            # Resolve relative path
            target_path = (md_file.parent / link).resolve()

            # Check if target exists
            if not target_path.exists():
                # Try with .md extension if it's missing (common in some markdown flavors)
                if not target_path.with_suffix(".md").exists():
                    errors.append(
                        f"Broken link in {md_file.relative_to(root_dir)}: {link} (Resolved to: {target_path})"
                    )

    if errors:
        logging.info("Found broken internal links:")
        for error in errors:
            logging.error(f"  - {error}")
        return False

    logging.info("All internal links are valid.")
    return True


if __name__ == "__main__":
    if not check_links():
        sys.exit(1)
    sys.exit(0)
