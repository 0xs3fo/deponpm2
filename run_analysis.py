#!/usr/bin/env python3
"""
Simple script to run the Bug Bounty Package Analyzer
"""
import asyncio
import sys
from pathlib import Path

# Add src directory to path
sys.path.append(str(Path(__file__).parent / "src"))

from main import BugBountyAnalyzer

async def main():
    """Main function to run the analysis"""
    
    # Get organization name from command line or prompt
    if len(sys.argv) > 1:
        org_name = sys.argv[1]
    else:
        org_name = input("Enter GitHub organization name: ").strip()
    
    if not org_name:
        print("Error: Organization name is required")
        sys.exit(1)
    
    # Get GitHub token from environment or prompt
    import os
    github_token = os.getenv('GITHUB_TOKEN')
    if not github_token:
        github_token = input("Enter GitHub token (optional, press Enter to skip): ").strip()
        if not github_token:
            github_token = None
    
    print(f"Analyzing organization: {org_name}")
    if github_token:
        print("Using GitHub token for higher rate limits")
    else:
        print("Running without GitHub token (limited rate limits)")
    
    # Initialize analyzer
    analyzer = BugBountyAnalyzer(
        github_token=github_token,
        output_dir=Path("./results")
    )
    
    try:
        # Run analysis
        results = await analyzer.analyze_organization(
            org_name=org_name,
            include_private=False,  # Set to True if you want to include private repos
            include_deleted=True,
            max_repos=10  # Limit for demo purposes
        )
        
        print("\n" + "="*50)
        print("ANALYSIS COMPLETED!")
        print("="*50)
        print(f"Repositories analyzed: {len(results.get('repositories', []))}")
        print(f"Packages found: {len(results.get('packages', []))}")
        print(f"Commits analyzed: {len(results.get('commits', []))}")
        
        # Count vulnerable and unclaimed packages
        packages = results.get('packages', [])
        vulnerable = sum(1 for pkg in packages if pkg.get('is_vulnerable', False))
        unclaimed = sum(1 for pkg in packages if pkg.get('is_unclaimed', False))
        
        print(f"Vulnerable packages: {vulnerable}")
        print(f"Unclaimed packages: {unclaimed}")
        print(f"Results saved to: ./results/")
        
    except KeyboardInterrupt:
        print("\nAnalysis interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error during analysis: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
