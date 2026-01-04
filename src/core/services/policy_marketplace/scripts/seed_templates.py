"""
Constitutional Hash: cdd01ef066bc6cf2
"""

#!/usr/bin/env python3
"""
Seed script for verified policy templates in the Policy Marketplace.

This script loads verified template JSON files from the templates/verified directory
and inserts them into the database with is_verified=true and status='published'.

Usage:
    cd acgs2-core/services/policy_marketplace
    python scripts/seed_templates.py

Environment Variables:
    MARKETPLACE_DATABASE_URL: PostgreSQL connection URL
        (default: postgresql+asyncpg://acgs2_user:acgs2_pass@localhost:5432/acgs2_marketplace)
"""
# ruff: noqa: I001

import asyncio
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


# Template directory path
TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "verified"

# Default database URL
DEFAULT_DATABASE_URL = "postgresql+asyncpg://acgs2_user:acgs2_pass@localhost:5432/acgs2_marketplace"


def get_database_url() -> str:
    """Get database URL from environment or use default."""
    return os.getenv("MARKETPLACE_DATABASE_URL", DEFAULT_DATABASE_URL)


def compute_content_hash(content: str) -> str:
    """Compute SHA-256 hash of content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def load_template_file(file_path: Path) -> dict:
    """Load and parse a template JSON file."""
    with open(file_path, encoding="utf-8") as f:
        return json.load(f)


def get_verified_templates() -> list[dict]:
    """Load all verified template files from the templates directory."""
    templates = []

    if not TEMPLATES_DIR.exists():
        raise FileNotFoundError(f"Templates directory not found: {TEMPLATES_DIR}")

    for file_path in sorted(TEMPLATES_DIR.glob("*.json")):
        try:
            template_data = load_template_file(file_path)

            # Extract metadata from template file
            template = {
                "name": template_data.get("name", file_path.stem),
                "description": template_data.get("description", ""),
                "category": template_data.get("category", "custom"),
                "format": template_data.get("format", "json"),
                "version": template_data.get("version", "1.0.0"),
                "author_name": template_data.get("author", "ACGS-2 Team"),
                "content": json.dumps(template_data, indent=2),
                "tags": template_data.get("tags", []),
                "file_name": file_path.name,
            }
            templates.append(template)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {file_path}: {e}") from e

    return templates


async def seed_templates(dry_run: bool = False) -> int:
    """
    Seed verified templates into the database.

    Args:
        dry_run: If True, only validate templates without inserting.

    Returns:
        Number of templates seeded.
    """
    templates = get_verified_templates()

    if not templates:
        raise ValueError("No template files found in templates/verified directory")

    if dry_run:
        for template in templates:
            print(f"  [DRY RUN] Would seed: {template['name']} ({template['category']})")
        return len(templates)

    # Create async engine
    engine = create_async_engine(
        get_database_url(),
        echo=False,
    )

    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    seeded_count = 0
    now = datetime.now(timezone.utc)

    async with async_session() as session:
        for template in templates:
            try:
                # Check if template already exists by name
                result = await session.execute(
                    text("SELECT id FROM templates WHERE name = :name"),
                    {"name": template["name"]},
                )
                existing = result.scalar_one_or_none()

                if existing:
                    print(f"  [SKIP] Template already exists: {template['name']}")
                    continue

                # Compute content hash
                content_hash = compute_content_hash(template["content"])

                # Insert template
                await session.execute(
                    text(
                        """
                        INSERT INTO templates (
                            name, description, content, category, format,
                            status, is_verified, is_public, is_deleted,
                            author_name, current_version, downloads, rating_count,
                            created_at, updated_at
                        ) VALUES (
                            :name, :description, :content, :category, :format,
                            'published', true, true, false,
                            :author_name, :version, 0, 0,
                            :now, :now
                        )
                        RETURNING id
                    """
                    ),
                    {
                        "name": template["name"],
                        "description": template["description"],
                        "content": template["content"],
                        "category": template["category"],
                        "format": template["format"],
                        "author_name": template["author_name"],
                        "version": template["version"],
                        "now": now,
                    },
                )

                # Get the inserted template ID
                result = await session.execute(
                    text("SELECT id FROM templates WHERE name = :name"),
                    {"name": template["name"]},
                )
                template_id = result.scalar_one()

                # Insert initial version
                await session.execute(
                    text(
                        """
                        INSERT INTO template_versions (
                            template_id, version, content, content_hash,
                            changelog, created_by, created_at
                        ) VALUES (
                            :template_id, :version, :content, :content_hash,
                            :changelog, :created_by, :now
                        )
                    """
                    ),
                    {
                        "template_id": template_id,
                        "version": template["version"],
                        "content": template["content"],
                        "content_hash": content_hash,
                        "changelog": "Initial verified release",
                        "created_by": "system",
                        "now": now,
                    },
                )

                seeded_count += 1
                print(f"  [OK] Seeded: {template['name']} ({template['category']})")

            except Exception as e:
                print(f"  [ERROR] Failed to seed {template['name']}: {e}")
                raise

        # Commit all changes
        await session.commit()

    # Cleanup
    await engine.dispose()

    return seeded_count


async def verify_seed() -> int:
    """Verify the number of verified templates in the database."""
    engine = create_async_engine(get_database_url(), echo=False)

    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT COUNT(*) FROM templates WHERE is_verified = true"))
        count = result.scalar_one()

    await engine.dispose()
    return count


async def main():
    """Main entry point for the seed script."""
    print("=" * 60)
    print("Policy Marketplace - Verified Templates Seed Script")
    print("=" * 60)
    print()

    # Check for dry run flag
    dry_run = "--dry-run" in sys.argv

    if dry_run:
        print("Mode: DRY RUN (no database changes)")
    else:
        print(f"Database: {get_database_url()}")
    print(f"Templates directory: {TEMPLATES_DIR}")
    print()

    # Load and validate templates
    print("Loading templates...")
    try:
        templates = get_verified_templates()
        print(f"Found {len(templates)} template files")
        print()
    except Exception as e:
        print(f"ERROR: Failed to load templates: {e}")
        sys.exit(1)

    # Seed templates
    print("Seeding templates...")
    try:
        seeded_count = await seed_templates(dry_run=dry_run)
        print()
        print(f"Successfully seeded {seeded_count} templates")
    except Exception as e:
        print(f"ERROR: Failed to seed templates: {e}")
        sys.exit(1)

    # Verify seed (skip for dry run)
    if not dry_run:
        print()
        print("Verifying seed...")
        try:
            verified_count = await verify_seed()
            print(f"Total verified templates in database: {verified_count}")
        except Exception as e:
            print(f"WARNING: Could not verify seed: {e}")

    print()
    print("=" * 60)
    print("Seed completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
