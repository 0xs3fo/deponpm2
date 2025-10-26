"""
Commit history analysis including deleted commits and file changes
"""
import logging
from pathlib import Path
from typing import List, Dict, Optional, Set
from github.Repository import Repository
from github_client import GitHubClient

# Import settings with fallback
try:
    from config.settings import MAX_CONCURRENT_COMMITS
except ImportError:
    MAX_CONCURRENT_COMMITS = 8

logger = logging.getLogger(__name__)

class CommitAnalyzer:
    """Analyzes commit history to extract package information and changes"""
    
    def __init__(self, github_client: GitHubClient):
        """
        Initialize commit analyzer
        
        Args:
            github_client: GitHub API client instance
        """
        self.github_client = github_client
        self.analyzed_commits = []
        self.package_changes = []
    
    def analyze_repository_commits(self, repo: Repository, since: Optional[str] = None) -> List[Dict]:
        """
        Analyze all commits in a repository
        
        Args:
            repo: GitHub Repository object
            since: ISO date string to get commits since (optional)
            
        Returns:
            List of analyzed commit data
        """
        logger.info(f"Analyzing commits for repository: {repo.full_name}")
        
        try:
            # Get all commits from GitHub API
            commits = self.github_client.get_repository_commits(repo, since)
            
            analyzed_commits = []
            for commit_data in commits:
                analyzed_commit = self._analyze_single_commit(commit_data, repo)
                if analyzed_commit:
                    analyzed_commits.append(analyzed_commit)
            
            logger.info(f"Analyzed {len(analyzed_commits)} commits for {repo.full_name}")
            return analyzed_commits
            
        except Exception as e:
            logger.error(f"Error analyzing commits for {repo.full_name}: {e}")
            return []
    
    def _analyze_single_commit(self, commit_data: Dict, repo: Repository) -> Optional[Dict]:
        """
        Analyze a single commit for package-related changes
        
        Args:
            commit_data: Commit data from GitHub API
            repo: Repository object
            
        Returns:
            Analyzed commit data or None if no package changes
        """
        try:
            analyzed_commit = {
                'sha': commit_data['sha'],
                'message': commit_data['message'],
                'author': commit_data['author'],
                'committer': commit_data['committer'],
                'url': commit_data['url'],
                'package_changes': [],
                'deleted_files': [],
                'modified_files': [],
                'added_files': []
            }
            
            package_changes_found = False
            
            # Analyze each file change in the commit
            for file_change in commit_data.get('files_changed', []):
                file_info = self._analyze_file_change(file_change, repo, commit_data['sha'])
                
                if file_info:
                    analyzed_commit['package_changes'].append(file_info)
                    package_changes_found = True
                
                # Categorize file changes
                status = file_change.get('status', '')
                if status == 'deleted':
                    analyzed_commit['deleted_files'].append(file_change['filename'])
                elif status == 'modified':
                    analyzed_commit['modified_files'].append(file_change['filename'])
                elif status == 'added':
                    analyzed_commit['added_files'].append(file_change['filename'])
            
            # Only return commits that have package-related changes
            if package_changes_found:
                return analyzed_commit
            
            return None
            
        except Exception as e:
            logger.error(f"Error analyzing commit {commit_data.get('sha', 'unknown')}: {e}")
            return None
    
    def _analyze_file_change(self, file_change: Dict, repo: Repository, commit_sha: str) -> Optional[Dict]:
        """
        Analyze a single file change for package information
        
        Args:
            file_change: File change data from GitHub API
            repo: Repository object
            commit_sha: Commit SHA for reference
            
        Returns:
            File analysis data or None if not a package file
        """
        filename = file_change.get('filename', '')
        status = file_change.get('status', '')
        
        # Check if this is a package file
        package_type = self._identify_package_file(filename)
        if not package_type:
            return None
        
        try:
            file_info = {
                'filename': filename,
                'status': status,
                'package_type': package_type,
                'additions': file_change.get('additions', 0),
                'deletions': file_change.get('deletions', 0),
                'changes': file_change.get('changes', 0),
                'commit_sha': commit_sha,
                'packages': []
            }
            
            # Get file content based on status
            if status == 'deleted':
                # For deleted files, we can't get current content, but we might have patch data
                patch = file_change.get('patch', '')
                if patch:
                    file_info['packages'] = self._extract_packages_from_patch(patch, package_type)
            else:
                # For added or modified files, get the file content
                content = self.github_client.get_repository_file_content(repo, filename, commit_sha)
                if content:
                    file_info['packages'] = self._extract_packages_from_content(content, package_type)
            
            return file_info
            
        except Exception as e:
            logger.error(f"Error analyzing file change {filename}: {e}")
            return None
    
    def _identify_package_file(self, filename: str) -> Optional[str]:
        """
        Identify if a file is a package file and return its type
        
        Args:
            filename: Name of the file
            
        Returns:
            Package type or None if not a package file
        """
        filename_lower = filename.lower()
        
        # Check for various package file patterns
        if filename_lower.endswith('package.json'):
            return 'npm'
        elif filename_lower.endswith('yarn.lock'):
            return 'yarn'
        elif filename_lower.endswith('requirements.txt'):
            return 'pip'
        elif filename_lower.endswith('setup.py'):
            return 'pip'
        elif filename_lower.endswith('pyproject.toml'):
            return 'pip'
        elif filename_lower.endswith('pom.xml'):
            return 'maven'
        elif filename_lower.endswith('build.gradle') or filename_lower.endswith('build.gradle.kts'):
            return 'gradle'
        elif filename_lower.endswith('composer.json'):
            return 'composer'
        elif filename_lower.endswith('cargo.toml'):
            return 'cargo'
        elif filename_lower.endswith('go.mod') or filename_lower.endswith('go.sum'):
            return 'go'
        elif filename_lower.endswith('gemfile') or filename_lower.endswith('gemfile.lock'):
            return 'ruby'
        elif filename_lower.endswith('packages.config'):
            return 'nuget'
        elif filename_lower.endswith('.csproj') or filename_lower.endswith('.vbproj'):
            return 'nuget'
        
        return None
    
    def _extract_packages_from_content(self, content: str, package_type: str) -> List[Dict]:
        """
        Extract package information from file content
        
        Args:
            content: File content as string
            package_type: Type of package file
            
        Returns:
            List of package dictionaries
        """
        packages = []
        
        try:
            if package_type == 'npm':
                packages = self._extract_npm_packages(content)
            elif package_type == 'pip':
                packages = self._extract_pip_packages(content)
            elif package_type == 'maven':
                packages = self._extract_maven_packages(content)
            elif package_type == 'gradle':
                packages = self._extract_gradle_packages(content)
            elif package_type == 'composer':
                packages = self._extract_composer_packages(content)
            elif package_type == 'cargo':
                packages = self._extract_cargo_packages(content)
            elif package_type == 'go':
                packages = self._extract_go_packages(content)
            elif package_type == 'ruby':
                packages = self._extract_ruby_packages(content)
            elif package_type == 'nuget':
                packages = self._extract_nuget_packages(content)
            
        except Exception as e:
            logger.error(f"Error extracting packages from {package_type} content: {e}")
        
        return packages
    
    def _extract_packages_from_patch(self, patch: str, package_type: str) -> List[Dict]:
        """
        Extract package information from git patch data
        
        Args:
            patch: Git patch content
            package_type: Type of package file
            
        Returns:
            List of package dictionaries
        """
        # This is a simplified implementation
        # In a real implementation, you'd parse the patch to extract added/removed lines
        packages = []
        
        try:
            # Look for package additions in the patch
            lines = patch.split('\n')
            for line in lines:
                if line.startswith('+') and not line.startswith('+++'):
                    # This is an added line, extract package info
                    content = line[1:]  # Remove the '+' prefix
                    extracted = self._extract_packages_from_content(content, package_type)
                    packages.extend(extracted)
        except Exception as e:
            logger.error(f"Error extracting packages from patch: {e}")
        
        return packages
    
    def _extract_npm_packages(self, content: str) -> List[Dict]:
        """Extract packages from package.json content"""
        import json
        packages = []
        
        try:
            data = json.loads(content)
            
            # Extract dependencies
            for deps_key in ['dependencies', 'devDependencies', 'peerDependencies', 'optionalDependencies']:
                if deps_key in data and isinstance(data[deps_key], dict):
                    for name, version in data[deps_key].items():
                        packages.append({
                            'name': name,
                            'version': version,
                            'type': 'dependency',
                            'category': deps_key
                        })
            
            # Extract package name and version
            if 'name' in data:
                packages.append({
                    'name': data['name'],
                    'version': data.get('version', 'unknown'),
                    'type': 'package',
                    'category': 'main'
                })
                
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing package.json: {e}")
        
        return packages
    
    def _extract_pip_packages(self, content: str) -> List[Dict]:
        """Extract packages from requirements.txt or setup.py content"""
        packages = []
        
        try:
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Parse package specification
                    if '==' in line:
                        name, version = line.split('==', 1)
                    elif '>=' in line:
                        name, version = line.split('>=', 1)
                    elif '~=' in line:
                        name, version = line.split('~=', 1)
                    else:
                        name = line
                        version = 'unknown'
                    
                    packages.append({
                        'name': name.strip(),
                        'version': version.strip(),
                        'type': 'dependency',
                        'category': 'pip'
                    })
        except Exception as e:
            logger.error(f"Error parsing pip requirements: {e}")
        
        return packages
    
    def _extract_maven_packages(self, content: str) -> List[Dict]:
        """Extract packages from pom.xml content"""
        # This is a simplified implementation
        # In a real implementation, you'd use XML parsing
        packages = []
        # TODO: Implement Maven package extraction
        return packages
    
    def _extract_gradle_packages(self, content: str) -> List[Dict]:
        """Extract packages from build.gradle content"""
        packages = []
        # TODO: Implement Gradle package extraction
        return packages
    
    def _extract_composer_packages(self, content: str) -> List[Dict]:
        """Extract packages from composer.json content"""
        import json
        packages = []
        
        try:
            data = json.loads(content)
            
            # Extract dependencies
            for deps_key in ['require', 'require-dev']:
                if deps_key in data and isinstance(data[deps_key], dict):
                    for name, version in data[deps_key].items():
                        packages.append({
                            'name': name,
                            'version': version,
                            'type': 'dependency',
                            'category': deps_key
                        })
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing composer.json: {e}")
        
        return packages
    
    def _extract_cargo_packages(self, content: str) -> List[Dict]:
        """Extract packages from Cargo.toml content"""
        packages = []
        # TODO: Implement Cargo package extraction
        return packages
    
    def _extract_go_packages(self, content: str) -> List[Dict]:
        """Extract packages from go.mod content"""
        packages = []
        # TODO: Implement Go package extraction
        return packages
    
    def _extract_ruby_packages(self, content: str) -> List[Dict]:
        """Extract packages from Gemfile content"""
        packages = []
        # TODO: Implement Ruby package extraction
        return packages
    
    def _extract_nuget_packages(self, content: str) -> List[Dict]:
        """Extract packages from packages.config or .csproj content"""
        packages = []
        # TODO: Implement NuGet package extraction
        return packages
    
    def get_analysis_statistics(self) -> Dict:
        """
        Get statistics about the commit analysis
        
        Returns:
            Dictionary with analysis statistics
        """
        total_commits = len(self.analyzed_commits)
        total_package_changes = sum(len(commit.get('package_changes', [])) for commit in self.analyzed_commits)
        
        package_types = {}
        for commit in self.analyzed_commits:
            for change in commit.get('package_changes', []):
                pkg_type = change.get('package_type', 'unknown')
                package_types[pkg_type] = package_types.get(pkg_type, 0) + 1
        
        return {
            'total_commits_analyzed': total_commits,
            'total_package_changes': total_package_changes,
            'package_types': package_types,
            'commits_with_package_changes': total_commits
        }
