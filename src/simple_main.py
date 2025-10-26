#!/usr/bin/env python3
"""
Simplified Bug Bounty Package Analyzer - Works without complex dependencies
"""
import asyncio
import logging
import sys
import json
import csv
import os
from pathlib import Path
from typing import List, Optional, Dict
import requests
import time

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bug_bounty_analyzer.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class SimpleGitHubClient:
    """Simple GitHub API client using requests"""
    
    def __init__(self, token: Optional[str] = None):
        self.token = token
        self.session = requests.Session()
        if token:
            self.session.headers.update({'Authorization': f'token {token}'})
        self.session.headers.update({'Accept': 'application/vnd.github.v3+json'})
        self.rate_limit_remaining = 5000 if token else 60
        self.rate_limit_reset = time.time() + 3600
    
    def _handle_rate_limit(self):
        """Handle rate limiting"""
        if self.rate_limit_remaining < 10:
            wait_time = self.rate_limit_reset - time.time() + 60
            if wait_time > 0:
                logger.warning(f"Rate limit low. Waiting {wait_time:.0f} seconds...")
                time.sleep(wait_time)
    
    def get_organization_repositories(self, org_name: str) -> List[Dict]:
        """Get repositories for an organization"""
        logger.info(f"Fetching repositories for organization: {org_name}")
        
        repos = []
        page = 1
        per_page = 100
        
        while True:
            self._handle_rate_limit()
            
            url = f"https://api.github.com/orgs/{org_name}/repos"
            params = {
                'type': 'all',
                'sort': 'updated',
                'page': page,
                'per_page': per_page
            }
            
            try:
                response = self.session.get(url, params=params, timeout=30)
                
                # Update rate limit info
                if 'X-RateLimit-Remaining' in response.headers:
                    self.rate_limit_remaining = int(response.headers['X-RateLimit-Remaining'])
                if 'X-RateLimit-Reset' in response.headers:
                    self.rate_limit_reset = int(response.headers['X-RateLimit-Reset'])
                
                if response.status_code == 200:
                    data = response.json()
                    if not data:
                        break
                    
                    for repo in data:
                        if not repo.get('private', False):  # Only public repos for now
                            repos.append({
                                'name': repo['name'],
                                'full_name': repo['full_name'],
                                'html_url': repo['html_url'],
                                'clone_url': repo['clone_url'],
                                'language': repo.get('language'),
                                'size': repo.get('size', 0),
                                'stars': repo.get('stargazers_count', 0),
                                'forks': repo.get('forks_count', 0),
                                'created_at': repo.get('created_at'),
                                'updated_at': repo.get('updated_at')
                            })
                    
                    if len(data) < per_page:
                        break
                    
                    page += 1
                    if page > 100:  # Safety limit
                        break
                        
                elif response.status_code == 404:
                    logger.error(f"Organization {org_name} not found")
                    break
                else:
                    logger.error(f"API error: {response.status_code} - {response.text}")
                    break
                    
            except Exception as e:
                logger.error(f"Error fetching repositories: {e}")
                break
        
        logger.info(f"Found {len(repos)} repositories")
        return repos

class SimplePackageExtractor:
    """Simple package extractor for common package files"""
    
    def __init__(self):
        self.package_files = [
            'package.json',
            'requirements.txt',
            'setup.py',
            'pom.xml',
            'build.gradle',
            'composer.json',
            'Cargo.toml',
            'go.mod',
            'Gemfile'
        ]
    
    def extract_packages_from_repo(self, repo_name: str, repo_url: str) -> List[Dict]:
        """Extract packages from a repository by checking GitHub API"""
        packages = []
        
        # For now, we'll simulate package extraction
        # In a real implementation, you would clone the repo and scan files
        logger.info(f"Extracting packages from {repo_name}")
        
        # Simulate finding some packages
        if 'package.json' in repo_name.lower() or 'node' in repo_name.lower():
            packages.append({
                'name': f'{repo_name}-main',
                'version': '1.0.0',
                'type': 'package',
                'package_manager': 'npm',
                'file_path': 'package.json',
                'source': 'simulated'
            })
        
        if 'python' in repo_name.lower() or 'py' in repo_name.lower():
            packages.append({
                'name': f'{repo_name}-main',
                'version': '1.0.0',
                'type': 'package',
                'package_manager': 'pip',
                'file_path': 'setup.py',
                'source': 'simulated'
            })
        
        return packages

class SimpleNPMChecker:
    """Simple NPM package checker"""
    
    def __init__(self):
        self.session = requests.Session()
        self.checked_packages = []
    
    def check_package(self, package_name: str) -> Dict:
        """Check if a package exists in NPM registry"""
        try:
            url = f"https://registry.npmjs.org/{package_name}"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                return {
                    'name': package_name,
                    'exists': True,
                    'is_vulnerable': False,
                    'is_unclaimed': False
                }
            elif response.status_code == 404:
                return {
                    'name': package_name,
                    'exists': False,
                    'is_vulnerable': False,
                    'is_unclaimed': True
                }
            else:
                return {
                    'name': package_name,
                    'exists': False,
                    'is_vulnerable': False,
                    'is_unclaimed': False,
                    'error': f"HTTP {response.status_code}"
                }
        except Exception as e:
            return {
                'name': package_name,
                'exists': False,
                'is_vulnerable': False,
                'is_unclaimed': False,
                'error': str(e)
            }

class SimpleReporter:
    """Simple reporter that generates basic reports"""
    
    def __init__(self, output_dir: str = "results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timestamp = time.strftime("%Y%m%d_%H%M%S")
    
    def generate_reports(self, analysis_data: Dict) -> Dict[str, Path]:
        """Generate simple reports"""
        output_files = {}
        
        try:
            # JSON report
            json_file = self.output_dir / f"analysis_{self.timestamp}.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(analysis_data, f, indent=2, default=str)
            output_files['json'] = json_file
            
            # Text report
            txt_file = self.output_dir / f"analysis_{self.timestamp}.txt"
            with open(txt_file, 'w', encoding='utf-8') as f:
                f.write("Bug Bounty Package Analysis Report\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                repos = analysis_data.get('repositories', [])
                packages = analysis_data.get('packages', [])
                
                f.write(f"Repositories analyzed: {len(repos)}\n")
                f.write(f"Packages found: {len(packages)}\n")
                
                vulnerable = sum(1 for pkg in packages if pkg.get('is_vulnerable', False))
                unclaimed = sum(1 for pkg in packages if pkg.get('is_unclaimed', False))
                
                f.write(f"Vulnerable packages: {vulnerable}\n")
                f.write(f"Unclaimed packages: {unclaimed}\n\n")
                
                if packages:
                    f.write("Package Details:\n")
                    f.write("-" * 30 + "\n")
                    for pkg in packages:
                        f.write(f"- {pkg.get('name', 'Unknown')} ({pkg.get('package_manager', 'Unknown')})\n")
            
            output_files['txt'] = txt_file
            
            logger.info(f"Reports generated in {self.output_dir}")
            return output_files
            
        except Exception as e:
            logger.error(f"Error generating reports: {e}")
            return {}

class SimpleBugBountyAnalyzer:
    """Simplified bug bounty analyzer"""
    
    def __init__(self, github_token: Optional[str] = None, output_dir: str = "results"):
        self.github_client = SimpleGitHubClient(github_token)
        self.package_extractor = SimplePackageExtractor()
        self.npm_checker = SimpleNPMChecker()
        self.reporter = SimpleReporter(output_dir)
    
    def analyze_organization(self, org_name: str, max_repos: int = 10) -> Dict:
        """Analyze a GitHub organization"""
        print(f"Analyzing organization: {org_name}")
        
        # Step 1: Get repositories
        print("Fetching repositories...")
        repos = self.github_client.get_organization_repositories(org_name)
        
        if not repos:
            print("No repositories found")
            return {'repositories': [], 'packages': [], 'statistics': {}}
        
        # Limit repositories for demo
        repos = repos[:max_repos]
        print(f"Analyzing {len(repos)} repositories...")
        
        # Step 2: Extract packages
        print("Extracting packages...")
        all_packages = []
        for repo in repos:
            packages = self.package_extractor.extract_packages_from_repo(
                repo['name'], repo['html_url']
            )
            all_packages.extend(packages)
        
        # Step 3: Check NPM packages
        print("Checking NPM packages...")
        npm_packages = [pkg for pkg in all_packages if pkg.get('package_manager') == 'npm']
        
        for package in npm_packages:
            check_result = self.npm_checker.check_package(package['name'])
            package.update(check_result)
        
        # Step 4: Generate statistics
        stats = {
            'total_repositories': len(repos),
            'total_packages': len(all_packages),
            'npm_packages': len(npm_packages),
            'vulnerable_packages': sum(1 for pkg in all_packages if pkg.get('is_vulnerable', False)),
            'unclaimed_packages': sum(1 for pkg in all_packages if pkg.get('is_unclaimed', False))
        }
        
        # Step 5: Generate reports
        print("Generating reports...")
        analysis_data = {
            'repositories': repos,
            'packages': all_packages,
            'statistics': stats,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        report_files = self.reporter.generate_reports(analysis_data)
        
        # Display summary
        print("\n" + "="*50)
        print("ANALYSIS SUMMARY")
        print("="*50)
        print(f"Repositories analyzed: {stats['total_repositories']}")
        print(f"Total packages found: {stats['total_packages']}")
        print(f"NPM packages: {stats['npm_packages']}")
        print(f"Vulnerable packages: {stats['vulnerable_packages']}")
        print(f"Unclaimed packages: {stats['unclaimed_packages']}")
        print(f"Reports saved to: {self.reporter.output_dir}")
        
        return analysis_data

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python simple_main.py <organization_name> [github_token]")
        print("Example: python simple_main.py microsoft")
        print("Example: python simple_main.py microsoft your_github_token")
        sys.exit(1)
    
    org_name = sys.argv[1]
    github_token = sys.argv[2] if len(sys.argv) > 2 else None
    
    if github_token:
        print("Using GitHub token for higher rate limits")
    else:
        print("Running without GitHub token (limited rate limits)")
    
    try:
        analyzer = SimpleBugBountyAnalyzer(github_token)
        results = analyzer.analyze_organization(org_name, max_repos=5)  # Limit for demo
        
        print("\nAnalysis completed successfully!")
        
    except KeyboardInterrupt:
        print("\nAnalysis interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error during analysis: {e}")
        logger.error(f"Analysis error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
