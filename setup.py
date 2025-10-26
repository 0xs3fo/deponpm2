#!/usr/bin/env python3
"""
Setup script for Bug Bounty Package Analyzer
"""
from setuptools import setup, find_packages
from pathlib import Path

# Read README file
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    requirements = requirements_file.read_text(encoding="utf-8").strip().split('\n')
    requirements = [req.strip() for req in requirements if req.strip() and not req.startswith('#')]

setup(
    name="bug-bounty-package-analyzer",
    version="1.0.0",
    description="A comprehensive bug bounty hunting tool that analyzes GitHub organizations for potentially vulnerable or unclaimed packages",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Bug Bounty Team",
    author_email="bugbounty@example.com",
    url="https://github.com/your-username/bug-bounty-package-analyzer",
    packages=find_packages(),
    include_package_data=True,
    install_requires=requirements,
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "bug-bounty-analyzer=src.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "Topic :: Security",
        "Topic :: Software Development :: Testing",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    keywords="bug-bounty security vulnerability package-analysis github npm",
    project_urls={
        "Bug Reports": "https://github.com/your-username/bug-bounty-package-analyzer/issues",
        "Source": "https://github.com/your-username/bug-bounty-package-analyzer",
        "Documentation": "https://github.com/your-username/bug-bounty-package-analyzer#readme",
    },
)
