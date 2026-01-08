"""Constitutional Hash: cdd01ef066bc6cf2
Setup configuration for ACGS-2 Core package.

Provides the acgs2-policy CLI command for Rego policy validation and testing.
"""

from setuptools import find_packages, setup

setup(
    name="src-core",
    version="0.1.0",
    description="ACGS-2 Core - Policy validation and testing tools",
    author="ACGS2 Team",
    python_requires=">=3.11",
    packages=find_packages(exclude=["tests", "tests.*"]),
    install_requires=[
        "typer>=0.9.0",
        "rich>=13.0.0",
        "httpx>=0.25.0",
        "pydantic>=2.12.0",
    ],
    extras_require={
        "playground": [
            "fastapi>=0.127.0",
            "uvicorn[standard]>=0.40.0",
        ],
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "acgs2-policy=cli.policy_cli:app",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Testing",
        "Topic :: System :: Systems Administration",
    ],
)
