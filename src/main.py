"""
Main entry point for the Bug Bounty Package Analyzer
"""
import asyncio
import logging
import sys
from pathlib import Path
from typing import List, Optional
import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

# Add src directory to path
sys.path.append(str(Path(__file__).parent))

from github_client import GitHubClient
from repo_cloner import RepositoryCloner
from commit_analyzer import CommitAnalyzer
from package_extractor import PackageExtractor
from npm_checker import NPMChecker
from reporter import Reporter

# Import settings with fallback
try:
    from config.settings import LOG_LEVEL, LOG_FORMAT, LOG_FILE, MAX_CONCURRENT_REPOS
except ImportError:
    # Fallback values if config not available
    LOG_LEVEL = 'INFO'
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_FILE = 'bug_bounty_analyzer.log'
    MAX_CONCURRENT_REPOS = 4

# Set up logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT,
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
console = Console()

class BugBountyAnalyzer:
    """Main analyzer class that orchestrates the entire analysis process"""
    
    def __init__(self, github_token: Optional[str] = None, output_dir: Optional[Path] = None):
        """
        Initialize the analyzer
        
        Args:
            github_token: GitHub personal access token
            output_dir: Output directory for results
        """
        self.github_token = github_token
        self.output_dir = Path(output_dir) if output_dir else Path("results")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.github_client = GitHubClient(github_token)
        self.repo_cloner = RepositoryCloner()
        self.commit_analyzer = CommitAnalyzer(self.github_client)
        self.package_extractor = PackageExtractor()
        self.npm_checker = NPMChecker()
        self.reporter = Reporter(self.output_dir)
        
        # Analysis results
        self.analysis_results = {
            'repositories': [],
            'packages': [],
            'commits': [],
            'npm_checks': {},
            'statistics': {}
        }
    
    async def analyze_organization(self, 
                                 org_name: str, 
                                 include_private: bool = False,
                                 include_deleted: bool = True,
                                 max_repos: Optional[int] = None) -> Dict:
        """
        Analyze a GitHub organization for potentially vulnerable packages
        
        Args:
            org_name: Name of the GitHub organization
            include_private: Whether to include private repositories
            include_deleted: Whether to analyze deleted commits
            max_repos: Maximum number of repositories to analyze (None for all)
            
        Returns:
            Analysis results dictionary
        """
        console.print(f"[bold blue]Starting analysis of organization: {org_name}[/bold blue]")
        
        try:
            # Step 1: Get organization repositories
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Fetching repositories...", total=None)
                
                repos = self.github_client.get_organization_repositories(org_name, include_private)
                if max_repos:
                    repos = repos[:max_repos]
                
                progress.update(task, description=f"Found {len(repos)} repositories")
            
            if not repos:
                console.print("[red]No repositories found for the organization[/red]")
                return self.analysis_results
            
            # Step 2: Clone repositories
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console
            ) as progress:
                task = progress.add_task("Cloning repositories...", total=len(repos))
                
                cloned_repos = self.repo_cloner.clone_repositories_parallel(
                    repos, 
                    include_private=include_private,
                    max_workers=MAX_CONCURRENT_REPOS
                )
                
                progress.update(task, completed=len(cloned_repos))
            
            self.analysis_results['repositories'] = cloned_repos
            
            # Step 3: Extract packages from cloned repositories
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console
            ) as progress:
                task = progress.add_task("Extracting packages...", total=len(cloned_repos))
                
                all_packages = []
                for repo_info in cloned_repos:
                    repo_path = Path(repo_info['path'])
                    packages = self.package_extractor.extract_packages_from_directory(repo_path)
                    all_packages.extend(packages)
                    progress.advance(task)
                
                self.analysis_results['packages'] = all_packages
            
            # Step 4: Analyze commits (if requested)
            if include_deleted:
                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    TaskProgressColumn(),
                    console=console
                ) as progress:
                    task = progress.add_task("Analyzing commits...", total=len(repos))
                    
                    all_commits = []
                    for repo in repos:
                        commits = self.commit_analyzer.analyze_repository_commits(repo)
                        all_commits.extend(commits)
                        progress.advance(task)
                    
                    self.analysis_results['commits'] = all_commits
            
            # Step 5: Check NPM packages
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=console
            ) as progress:
                task = progress.add_task("Checking NPM packages...", total=len(all_packages))
                
                checked_packages = await self.npm_checker.check_packages_async(all_packages)
                
                # Update packages with NPM check results
                package_map = {pkg['name']: pkg for pkg in all_packages}
                for checked_pkg in checked_packages:
                    if checked_pkg['name'] in package_map:
                        package_map[checked_pkg['name']].update(checked_pkg)
                
                progress.update(task, completed=len(checked_packages))
            
            # Step 6: Generate statistics
            self.analysis_results['statistics'] = {
                'repositories': self.repo_cloner.get_clone_statistics(),
                'packages': self.package_extractor.get_extraction_statistics(),
                'commits': self.commit_analyzer.get_analysis_statistics(),
                'npm_checks': self.npm_checker.get_check_statistics()
            }
            
            # Step 7: Generate reports
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Generating reports...", total=None)
                
                report_files = self.reporter.generate_reports(
                    self.analysis_results,
                    output_formats=['json', 'csv', 'html', 'txt']
                )
                
                progress.update(task, description="Reports generated")
            
            # Display summary
            self._display_summary()
            
            return self.analysis_results
            
        except Exception as e:
            logger.error(f"Error during analysis: {e}")
            console.print(f"[red]Analysis failed: {e}[/red]")
            return self.analysis_results
    
    def _display_summary(self):
        """Display analysis summary in the console"""
        stats = self.analysis_results.get('statistics', {})
        packages = self.analysis_results.get('packages', [])
        
        # Count vulnerable and unclaimed packages
        vulnerable_count = sum(1 for pkg in packages if pkg.get('is_vulnerable', False))
        unclaimed_count = sum(1 for pkg in packages if pkg.get('is_unclaimed', False))
        
        # Create summary table
        table = Table(title="Analysis Summary")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")
        
        table.add_row("Repositories Analyzed", str(len(self.analysis_results.get('repositories', []))))
        table.add_row("Total Packages Found", str(len(packages)))
        table.add_row("Vulnerable Packages", str(vulnerable_count), style="red" if vulnerable_count > 0 else "green")
        table.add_row("Unclaimed Packages", str(unclaimed_count), style="yellow" if unclaimed_count > 0 else "green")
        table.add_row("Commits Analyzed", str(len(self.analysis_results.get('commits', []))))
        
        console.print(table)
        
        # Display risk assessment
        if vulnerable_count > 0 or unclaimed_count > 0:
            risk_level = "HIGH" if (vulnerable_count + unclaimed_count) > 10 else "MEDIUM"
            console.print(f"\n[bold red]Risk Level: {risk_level}[/bold red]")
            
            if vulnerable_count > 0:
                console.print(f"[red]Found {vulnerable_count} potentially vulnerable packages[/red]")
            if unclaimed_count > 0:
                console.print(f"[yellow]Found {unclaimed_count} unclaimed packages[/yellow]")
        else:
            console.print("\n[bold green]No significant risks found[/bold green]")

@click.command()
@click.option('--org', required=True, help='GitHub organization name')
@click.option('--token', help='GitHub personal access token (optional but recommended)')
@click.option('--output', help='Output directory for results', default='./results')
@click.option('--private', is_flag=True, help='Include private repositories')
@click.option('--deleted', is_flag=True, default=True, help='Analyze deleted commits')
@click.option('--max-repos', type=int, help='Maximum number of repositories to analyze')
@click.option('--format', 'output_format', multiple=True, 
              type=click.Choice(['json', 'csv', 'html', 'txt']),
              default=['json', 'csv', 'html', 'txt'],
              help='Output formats for reports')
def main(org, token, output, private, deleted, max_repos, output_format):
    """
    Bug Bounty Package Analyzer
    
    Analyzes GitHub organizations for potentially vulnerable or unclaimed packages.
    """
    try:
        # Initialize analyzer
        analyzer = BugBountyAnalyzer(
            github_token=token,
            output_dir=Path(output)
        )
        
        # Run analysis
        results = asyncio.run(analyzer.analyze_organization(
            org_name=org,
            include_private=private,
            include_deleted=deleted,
            max_repos=max_repos
        ))
        
        console.print("\n[bold green]Analysis completed successfully![/bold green]")
        console.print(f"Results saved to: {Path(output).absolute()}")
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Analysis interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        logger.error(f"Main execution error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
