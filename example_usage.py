#!/usr/bin/env python3
"""
Example usage of the Bug Bounty Package Analyzer
"""
import asyncio
import sys
from pathlib import Path

# Add src directory to path
sys.path.append(str(Path(__file__).parent / "src"))

from main import BugBountyAnalyzer

async def example_analysis():
    """Example of how to use the analyzer programmatically"""
    
    # Initialize analyzer
    analyzer = BugBountyAnalyzer(
        github_token=None,  # Set your token here or use environment variable
        output_dir=Path("./example_results")
    )
    
    # Analyze an organization
    results = await analyzer.analyze_organization(
        org_name="microsoft",  # Example organization
        include_private=False,
        include_deleted=True,
        max_repos=5  # Limit for example
    )
    
    print("Analysis completed!")
    print(f"Found {len(results.get('packages', []))} packages")
    print(f"Analyzed {len(results.get('repositories', []))} repositories")

if __name__ == "__main__":
    asyncio.run(example_analysis())
